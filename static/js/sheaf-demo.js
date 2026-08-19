/*
 * Coordination sheaf demo — a JavaScript port of the Julia demo at
 * CellularSheaves.jl/examples/hexagon_coordination.
 *
 * The original ran the simulation in Julia and streamed frames to the browser over a
 * WebSocket. Everything here runs client-side instead: the per-frame numerical work is two
 * 18x18 solves, which is nothing for a browser and a great deal for a shared dyno.
 *
 * Section map, mirroring the Julia sources so the two stay diffable:
 *
 *   §0  constants                    HexagonDemo.jl:32-60
 *   §1  dense linear algebra         (replaces CliqueTrees.ChordalLDLt)
 *   §2  sheaf construction           Formations.jl, EuclideanSheaves.jl
 *   §3  simulation                   HexagonDemo.jl
 *   §4  renderer                     www/index.html
 *   §5  input                        www/index.html
 *   §6  mount / unmount              server.jl's frame loop
 *
 * §0-§3 touch no DOM at all: every `document` and `window` reference lives inside mount().
 * That is what lets the Node self-test load this file and exercise the mathematics headless,
 * and it is the one structural rule this file must not break.
 *
 * Loaded as a classic script, deliberately — not an ES module. In production these assets
 * are served from S3 while the page is on hansriess.com, and module scripts are always
 * fetched in CORS mode, so a module would work locally and fail only once deployed.
 */
(function (root) {
"use strict";

/* ===========================================================================
 * §0  Constants                                             HexagonDemo.jl:32-60
 * ======================================================================== */

var MAX_AGENTS = 6;
// Six agents admit C(6,2) = 15 distinct unordered pairs, so a complete graph is the ceiling
// and this cap is only ever reached there. Stated outright rather than left implicit in the
// duplicate-pair check.
var MAX_EDGES = 15;
var RADIUS = 0.55;
var D = 3;                       // two translation coordinates plus a homogeneous one
var MAX_RANK = D - 1;

// The arena the renderer draws, in the same units as the ring radius.
var ARENA_X = 4.0;
var ARENA_Y = 2.5;

var TARGET_ACCELERATION = 6.0;   // units/s^2 while a key is held
var TARGET_DAMPING = 3.2;        // 1/s, coasts to a stop on release
var TARGET_MAX_SPEED = 2.4;

// The target's terminal speed is ACCELERATION / DAMPING = 1.875, so a gain of 2.5 with no
// feedforward leaves a steady lag of about 0.75 units — roughly 1.4 ring radii.
var DEFAULT_GAIN = 2.5;
var DEFAULT_FEEDFORWARD = 0.0;
var AGENT_MAX_SPEED = 2.2;
var GAIN_MIN = 0.4;
var GAIN_MAX = 12.0;
var FEEDFORWARD_STEPS = [0.0, 0.5, 1.0];

var EPS = 2.220446049250313e-16;
// Julia's threshold is sqrt(eps) * max(1, ‖D‖∞) over LDLᵀ pivots; ours is the same constant
// against singular values. They are different quantities, but every topology this demo can
// reach has null directions at exact structural zeros (σ ≈ 1e-16 σmax), so there are about
// eight orders of magnitude of headroom either way.
var NULL_TOL_SCALE = Math.sqrt(EPS);

/* ===========================================================================
 * §1  Dense linear algebra
 *
 * One algorithm carries the whole file: one-sided Jacobi SVD. L_II is symmetric PSD, so its
 * SVD is its eigendecomposition — V's columns for σ ≈ 0 are an *orthonormal* null basis,
 * which is why the QR in HexagonDemo.jl:409 (`_orthonormal`) has no counterpart here.
 *
 * Jacobi is chosen over Golub–Kahan specifically for its high relative accuracy on tiny
 * singular values: every tolerance in this file is a smallness test. For the same reason
 * nothing here ever forms AᵀA — squaring would turn a 1e-7 threshold into 1e-14, which is
 * double-precision noise.
 * ======================================================================== */

function mat(rows, cols) {
    return { rows: rows, cols: cols, data: new Float64Array(rows * cols) };
}

function matFrom(rows, cols, values) {
    var m = mat(rows, cols);
    m.data.set(values);
    return m;
}

function identity(n) {
    var m = mat(n, n);
    for (var i = 0; i < n; i++) m.data[i * n + i] = 1;
    return m;
}

function transpose(A) {
    var T = mat(A.cols, A.rows);
    for (var i = 0; i < A.rows; i++) {
        for (var j = 0; j < A.cols; j++) T.data[j * A.rows + i] = A.data[i * A.cols + j];
    }
    return T;
}

// C = AᵀB, for the restriction-map products that build the Laplacian blocks.
function matTmul(A, B) {
    var C = mat(A.cols, B.cols);
    for (var k = 0; k < A.rows; k++) {
        for (var i = 0; i < A.cols; i++) {
            var a = A.data[k * A.cols + i];
            if (a === 0) continue;
            for (var j = 0; j < B.cols; j++) C.data[i * C.cols + j] += a * B.data[k * B.cols + j];
        }
    }
    return C;
}

function matmul(A, B) {
    var C = mat(A.rows, B.cols);
    for (var i = 0; i < A.rows; i++) {
        for (var k = 0; k < A.cols; k++) {
            var a = A.data[i * A.cols + k];
            if (a === 0) continue;
            for (var j = 0; j < B.cols; j++) C.data[i * C.cols + j] += a * B.data[k * B.cols + j];
        }
    }
    return C;
}

// out = A * x, writing into a caller-owned buffer so the per-frame path never allocates.
function matvec(A, x, out) {
    for (var i = 0; i < A.rows; i++) {
        var sum = 0;
        var base = i * A.cols;
        for (var j = 0; j < A.cols; j++) sum += A.data[base + j] * x[j];
        out[i] = sum;
    }
    return out;
}

/**
 * One-sided Jacobi SVD of a tall-or-square matrix. Requires rows >= cols, which every
 * caller here satisfies: L_II is 3n x 3n and `outside` is 3n x 2n.
 *
 * Returns { U (rows x cols), S (cols), V (cols x cols) } with S sorted descending.
 * Columns of U for negligible σ are left zero — no caller reads them.
 */
function svdTall(A) {
    var m = A.rows, n = A.cols;
    var a = Float64Array.from(A.data);          // working copy, rotated into U * Σ
    var v = identity(n).data;
    var p, q, i;

    for (var sweep = 0; sweep < 60; sweep++) {
        var offMax = 0;
        for (p = 0; p < n - 1; p++) {
            for (q = p + 1; q < n; q++) {
                var alpha = 0, beta = 0, gamma = 0;
                for (i = 0; i < m; i++) {
                    var ap = a[i * n + p], aq = a[i * n + q];
                    alpha += ap * ap; beta += aq * aq; gamma += ap * aq;
                }
                var denom = Math.sqrt(alpha * beta);
                if (denom === 0 || Math.abs(gamma) <= EPS * denom) continue;
                offMax = Math.max(offMax, Math.abs(gamma) / denom);

                var zeta = (beta - alpha) / (2 * gamma);
                var sign = zeta >= 0 ? 1 : -1;
                var t = sign / (Math.abs(zeta) + Math.sqrt(1 + zeta * zeta));
                var c = 1 / Math.sqrt(1 + t * t), s = c * t;

                for (i = 0; i < m; i++) {
                    var xp = a[i * n + p], xq = a[i * n + q];
                    a[i * n + p] = c * xp - s * xq;
                    a[i * n + q] = s * xp + c * xq;
                }
                for (i = 0; i < n; i++) {
                    var vp = v[i * n + p], vq = v[i * n + q];
                    v[i * n + p] = c * vp - s * vq;
                    v[i * n + q] = s * vp + c * vq;
                }
            }
        }
        if (offMax < EPS * 16) break;
    }

    // Singular values are the column norms of the rotated matrix.
    var sigma = new Float64Array(n);
    for (q = 0; q < n; q++) {
        var sum = 0;
        for (i = 0; i < m; i++) { var e = a[i * n + q]; sum += e * e; }
        sigma[q] = Math.sqrt(sum);
    }

    var order = [];
    for (q = 0; q < n; q++) order.push(q);
    order.sort(function (x, y) { return sigma[y] - sigma[x]; });

    var U = mat(m, n), V = mat(n, n), S = new Float64Array(n);
    for (var col = 0; col < n; col++) {
        var src = order[col];
        S[col] = sigma[src];
        var inv = sigma[src] > 0 ? 1 / sigma[src] : 0;
        for (i = 0; i < m; i++) U.data[i * n + col] = a[i * n + src] * inv;
        for (i = 0; i < n; i++) V.data[i * n + col] = v[i * n + src];
    }
    return { U: U, S: S, V: V };
}

/**
 * Left singular vectors and values of a 2 x k matrix — the per-agent blocks in
 * `translationBars`, and the only place the general routine's rows >= cols precondition
 * fails. Transposing hands the work back to svdTall: if Bᵀ = U'ΣV'ᵀ then B = V'ΣU'ᵀ, so B's
 * left singular vectors are V'. Going through BBᵀ instead would square the 1e-7 rank test
 * into 1e-14 and leave only a factor of ten above the noise floor.
 */
function svdLeft2(B) {
    var k = B.cols;
    if (k === 0) return { S: new Float64Array(0), u1: null };
    if (k === 1) {
        var x = B.data[0], y = B.data[1];
        var norm = Math.hypot(x, y);
        return { S: Float64Array.of(norm), u1: norm > 0 ? [x / norm, y / norm] : [1, 0] };
    }
    var f = svdTall(transpose(B));           // k x 2, so rows >= cols
    return { S: f.S, u1: [f.V.data[0], f.V.data[1]] };
}

// Columns of V whose singular value is negligible: an orthonormal basis for ker(A).
function nullBasis(factors) {
    var S = factors.S, V = factors.V, n = V.cols;
    var tol = NULL_TOL_SCALE * Math.max(1, S.length ? S[0] : 0);
    var keep = [];
    for (var j = 0; j < n; j++) if (S[j] <= tol) keep.push(j);

    var N = mat(V.rows, keep.length);
    for (var c = 0; c < keep.length; c++) {
        for (var i = 0; i < V.rows; i++) N.data[i * N.cols + c] = V.data[i * n + keep[c]];
    }
    return N;
}

/**
 * x = V Σ⁺ Uᵀ b, the minimum-norm solution of Ax = b.
 *
 * Julia's LDLᵀ path returns a different particular solution. That is provably invisible
 * downstream: `harmonicReference` projects onto the point of the solution set nearest the
 * agents' current configuration, and for orthonormal N, (I − NNᵀ)N = 0 — so any two
 * particular solutions differing by a null vector give the same answer.
 */
function pinvSolve(factors, b, out, scratch) {
    var U = factors.U, S = factors.S, V = factors.V;
    var n = S.length, i, j;
    var tol = NULL_TOL_SCALE * Math.max(1, n ? S[0] : 0);

    for (j = 0; j < n; j++) {
        if (S[j] <= tol) { scratch[j] = 0; continue; }
        var dot = 0;
        for (i = 0; i < U.rows; i++) dot += U.data[i * n + j] * b[i];
        scratch[j] = dot / S[j];
    }
    for (i = 0; i < V.rows; i++) {
        var sum = 0;
        for (j = 0; j < n; j++) sum += V.data[i * n + j] * scratch[j];
        out[i] = sum;
    }
    return out;
}

// out += N (Nᵀ v), the orthogonal projection of v onto range(N), accumulated into out.
function addProjection(N, v, out, scratch, scale) {
    var k = N.cols;
    if (k === 0) return out;
    var i, j;
    for (j = 0; j < k; j++) {
        var dot = 0;
        for (i = 0; i < N.rows; i++) dot += N.data[i * k + j] * v[i];
        scratch[j] = dot;
    }
    for (i = 0; i < N.rows; i++) {
        var sum = 0;
        for (j = 0; j < k; j++) sum += N.data[i * k + j] * scratch[j];
        out[i] += scale * sum;
    }
    return out;
}

/* ===========================================================================
 * §2  Sheaf construction                    Formations.jl, EuclideanSheaves.jl
 *
 * Agents are 0-based here; the target is vertex `n`. Julia is 1-based with the target at
 * `n+1`, so every index in a comment referring to the Julia source is one higher.
 * ======================================================================== */

// affine_translation_matrix(d) = [I₂ −d; 0 1].            Formations.jl:26
// Note the minus: with h = 1, edge (i,j) then asserts pᵢ − dᵢ = pⱼ − dⱼ.
function affineFrame(d) {
    return matFrom(3, 3, [1, 0, -d[0],
                          0, 1, -d[1],
                          0, 0, 1]);
}

/**
 * The (rank+1) x D matrix an agent applies to its stalk [p; h].    Formations.jl:285
 *
 * The last row is the *gauge* row [0 … 0 1], present at every rank and load-bearing:
 * affineFrame scales each offset by h, so a formation with h = 0 has its displacements
 * annihilated at zero Dirichlet energy — the ring collapses to a point. Without the gauge
 * row h is pinned only up to a constant and the Laplacian stays singular along exactly that
 * uniform dilation.
 *
 * Rank 0 means *no observation edge at all*, not a zero selector, and is handled by the
 * caller rather than here.
 */
function observationSelector(rank, u) {
    if (rank === 1) return matFrom(2, 3, [u[0], u[1], 0,
                                          0, 0, 1]);
    if (rank === MAX_RANK) return identity(3);
    throw new Error("observation rank must be 0, 1, or " + MAX_RANK + " (got " + rank + ")");
}

/**
 * The interior angle bisector at each vertex.                     Formations.jl:250
 *
 * The cyclic order is the agents' *creation* order, deliberately not the consensus wiring,
 * so a vertex has a well-defined bisector even before it has any edges. Two cases have no
 * angle to bisect and fall back to pointing at the centroid: a straight vertex, where the
 * rays cancel, and a vertex coincident with a neighbour, where a ray has no direction. The
 * three tolerances below are copied from the Julia exactly.
 */
function bisectorDirections(offsets) {
    var n = offsets.length;
    var cx = 0, cy = 0, i;
    for (i = 0; i < n; i++) { cx += offsets[i][0]; cy += offsets[i][1]; }
    cx /= n; cy /= n;

    function inward(here) {
        var tx = cx - here[0], ty = cy - here[1];
        var norm = Math.hypot(tx, ty);
        return norm > 1e-12 ? [tx / norm, ty / norm] : [1, 0];
    }

    var out = [];
    for (i = 0; i < n; i++) {
        var here = offsets[i];
        if (n < 3) { out.push(inward(here)); continue; }

        var prev = offsets[(i - 1 + n) % n], next = offsets[(i + 1) % n];
        var bx = prev[0] - here[0], by = prev[1] - here[1];
        var fx = next[0] - here[0], fy = next[1] - here[1];
        var nb = Math.hypot(bx, by), nf = Math.hypot(fx, fy);
        if (nb < 1e-12 || nf < 1e-12) { out.push(inward(here)); continue; }

        var ux = bx / nb + fx / nf, uy = by / nb + fy / nf;
        var nu = Math.hypot(ux, uy);
        out.push(nu < 1e-9 ? inward(here) : [ux / nu, uy / nu]);   // collinear → inward
    }
    return out;
}

/**
 * Build the projection escort sheaf.                       Formations.jl:444
 *
 * Consensus edges carry affineFrame on both sides — a fixed-displacement constraint.
 * Observation edges exist only for rank > 0 and carry S·frame[i] on the agent side, S on the
 * target side, so rank 1 asserts only uᵢᵀ(pᵢ − dᵢ) = uᵢᵀp_t.
 *
 * Edges are returned with u < v throughout, matching Graphs.jl's src < dst iteration.
 */
function buildSheaf(offsets, ranks, edges) {
    var n = offsets.length;
    var directions = bisectorDirections(offsets);
    var frames = offsets.map(affineFrame);
    var sheafEdges = [];
    var i;

    for (i = 0; i < edges.length; i++) {
        var a = edges[i][0], b = edges[i][1];
        sheafEdges.push({ u: a, v: b, rhoU: frames[a], rhoV: frames[b] });
    }
    for (i = 0; i < n; i++) {
        if (ranks[i] === 0) continue;
        var S = observationSelector(ranks[i], directions[i]);
        sheafEdges.push({ u: i, v: n, rhoU: matmul(S, frames[i]), rhoV: S });
    }
    return { nAgents: n, target: n, edges: sheafEdges, directions: directions, frames: frames };
}

/**
 * Interior-interior and interior-boundary Laplacian blocks, without ever assembling the full
 * Laplacian.                                              EuclideanSheaves.jl:320
 *
 * Interior is agents 0..n-1 in order, so agent i occupies dofs [3i, 3i+3). Boundary is the
 * single target vertex.
 */
function assembleBlocks(sheaf) {
    var n = sheaf.nAgents, target = sheaf.target;
    var nI = n * D;
    var LII = mat(nI, nI), LIB = mat(nI, D);

    function addBlock(dest, rowOff, colOff, block, sign) {
        for (var i = 0; i < block.rows; i++) {
            for (var j = 0; j < block.cols; j++) {
                dest.data[(rowOff + i) * dest.cols + colOff + j] += sign * block.data[i * block.cols + j];
            }
        }
    }

    for (var e = 0; e < sheaf.edges.length; e++) {
        var edge = sheaf.edges[e];
        var uI = edge.u < n, vI = edge.v < n;
        if (!uI && !vI) continue;                          // edge inside the boundary

        if (uI) addBlock(LII, edge.u * D, edge.u * D, matTmul(edge.rhoU, edge.rhoU), 1);
        if (vI) addBlock(LII, edge.v * D, edge.v * D, matTmul(edge.rhoV, edge.rhoV), 1);

        if (uI && vI) {
            var Duv = matTmul(edge.rhoU, edge.rhoV);
            addBlock(LII, edge.u * D, edge.v * D, Duv, -1);
            addBlock(LII, edge.v * D, edge.u * D, transpose(Duv), -1);
        } else if (uI && edge.v === target) {
            addBlock(LIB, edge.u * D, 0, matTmul(edge.rhoU, edge.rhoV), -1);
        } else if (vI && edge.u === target) {
            addBlock(LIB, edge.v * D, 0, matTmul(edge.rhoV, edge.rhoU), -1);
        }
    }
    return { LII: LII, LIB: LIB };
}

/**
 * Harmonic extension of boundary data at the target vertex.  EuclideanSheaves.jl:833
 *
 * Returns { x, nullSpace } where `x` covers the interior dofs (agent i at [3i, 3i+3)) and
 * the columns of `nullSpace` span the directions the boundary data leaves free.
 *
 * The running simulation does not call this — it caches the factorisation across frames,
 * since L_II depends only on topology. This is the unfactored reference version: the
 * self-test's entry point, and the thing to read when comparing against the Julia.
 */
function harmonicExtension(sheaf, boundary) {
    var blocks = assembleBlocks(sheaf);
    var factors = svdTall(blocks.LII);
    var nI = blocks.LII.rows;

    var rhs = new Float64Array(nI);
    matvec(blocks.LIB, boundary, rhs);
    for (var i = 0; i < nI; i++) rhs[i] = -rhs[i];

    var x = new Float64Array(nI);
    pinvSolve(factors, rhs, x, new Float64Array(nI));
    return { x: x, nullSpace: nullBasis(factors), factors: factors, LIB: blocks.LIB };
}

/**
 * Sheaf Dirichlet energy ‖δx‖² of the actual configuration — how far the fleet is from
 * satisfying its own coordination constraints right now.       HexagonDemo.jl:552
 *
 * The coboundary matrix is never materialised; this sums ‖ρᵤxᵤ − ρᵥxᵥ‖² edge by edge.
 */
function sheafEnergy(sheaf, positions, target) {
    var total = 0;
    var xu = [0, 0, 1], xv = [0, 0, 1];

    for (var e = 0; e < sheaf.edges.length; e++) {
        var edge = sheaf.edges[e];
        var pu = edge.u < sheaf.nAgents ? positions[edge.u] : target;
        var pv = edge.v < sheaf.nAgents ? positions[edge.v] : target;
        xu[0] = pu[0]; xu[1] = pu[1];
        xv[0] = pv[0]; xv[1] = pv[1];

        for (var r = 0; r < edge.rhoU.rows; r++) {
            var acc = 0;
            for (var c = 0; c < D; c++) {
                acc += edge.rhoU.data[r * D + c] * xu[c] - edge.rhoV.data[r * D + c] * xv[c];
            }
            total += acc * acc;
        }
    }
    return total;
}

/* ===========================================================================
 * §3  Simulation                                                  HexagonDemo.jl
 * ======================================================================== */

function regularOffsets(n, radius) {
    var out = [];
    for (var i = 0; i < n; i++) {
        var angle = i * 2 * Math.PI / n;
        out.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
    }
    return out;
}

// Normalised on the way in *and* on every lookup. The wrap-around edge is built as (n-1, 0),
// and leaving it unordered made exactly one edge of the ring — only that one — uncuttable.
function normaliseEdge(a, b) { return a < b ? [a, b] : [b, a]; }

function roundTo(x, digits) {
    var f = Math.pow(10, digits);
    return Math.round(x * f) / f;
}

function createSimulation(options) {
    var opts = options || {};

    var state = {
        radius: opts.radius === undefined ? RADIUS : opts.radius,
        ranks: [],
        edges: [],
        offsets: [],
        directions: [],
        positions: [],
        reference: [],
        target: [0, 0],
        velocity: [0, 0],
        command: [0, 0],
        gain: DEFAULT_GAIN,
        feedforward: DEFAULT_FEEDFORWARD,
        time: 0,
        // Cached by rebuild(); everything below depends on topology alone.
        sheaf: null,
        factors: null,
        LIB: null,
        nullSpace: null,
        barGroups: [],
        buffers: null,
        lastError: null
    };

    /* --- topology-dependent caches ------------------------------------- */

    /**
     * Rebuild the sheaf and re-cache everything the per-frame path needs.
     *
     * L_II depends only on ranks, wiring and offsets — exactly what triggers a rebuild — so
     * its factorisation is cached here alongside the null basis, as are the translation-bar
     * groups. Julia recomputes both harmonic extensions and the whole bar SVD every frame;
     * there is no reason to inherit that. What is left per frame is two matvecs, two
     * back-substitutions and a projection.
     */
    function rebuild() {
        var n = state.offsets.length;
        if (n === 0) {
            state.sheaf = null;
            state.factors = null;
            state.LIB = null;
            state.nullSpace = null;
            state.directions = [];
            state.barGroups = [];
            state.buffers = null;
            return;
        }

        state.sheaf = buildSheaf(state.offsets, state.ranks, state.edges);
        state.directions = state.sheaf.directions;

        var blocks = assembleBlocks(state.sheaf);
        state.factors = svdTall(blocks.LII);
        state.LIB = blocks.LIB;
        state.nullSpace = nullBasis(state.factors);
        state.barGroups = computeBarGroups(n, state.nullSpace);

        var nI = n * D;
        state.buffers = {
            boundary: new Float64Array(D),
            rhs: new Float64Array(nI),
            position: new Float64Array(nI),
            rate: new Float64Array(nI),
            current: new Float64Array(nI),
            delta: new Float64Array(nI),
            solveScratch: new Float64Array(nI),
            nullScratch: new Float64Array(Math.max(1, state.nullSpace.cols))
        };
    }

    /**
     * Which agents have a one-dimensional translational freedom, and along what direction.
     *                                                          HexagonDemo.jl:511
     *
     * A bar asserts one specific thing: *this line, and no other, is free*. That is true of
     * an agent whose translational freedom is one-dimensional — the classic single rank-1
     * observer, where everything may slide along the direction its lone reading cannot pin.
     * It is false of an agent with no observation at all, which is free in the whole plane
     * and has no distinguished direction; the null basis merely happens to pick two, and
     * drawing them would dress an arbitrary choice up as structure. Hence the "exactly one"
     * test below.
     *
     * Depends only on the null space, so it is computed on rebuild; only the bar's anchor
     * point moves per frame.
     */
    function computeBarGroups(n, N) {
        if (n === 0 || N === null || N.cols === 0) return [];

        // Pure translations of each agent, with the homogeneous slot left at zero.
        var translations = mat(n * D, 2 * n);
        for (var i = 0; i < n; i++) {
            for (var j = 0; j < 2; j++) {
                translations.data[(D * i + j) * translations.cols + (2 * i + j)] = 1;
            }
        }

        // What is left of each translation after removing its component inside the null
        // space; a translation is free exactly when nothing is left over.
        var NtT = matTmul(N, translations);
        var outside = matmul(N, NtT);
        for (var k = 0; k < outside.data.length; k++) {
            outside.data[k] = translations.data[k] - outside.data[k];
        }

        var factors = svdTall(outside);
        var sMax = factors.S.length ? factors.S[0] : 0;
        var tol = 1e-7 * Math.max(1, sMax);
        var free = [];
        for (var c = 0; c < factors.S.length; c++) if (factors.S[c] < tol) free.push(c);
        if (free.length === 0) return [];

        var groups = [];
        for (i = 0; i < n; i++) {
            var block = mat(2, free.length);
            for (var r = 0; r < 2; r++) {
                for (var f = 0; f < free.length; f++) {
                    block.data[r * free.length + f] =
                        factors.V.data[(2 * i + r) * factors.V.cols + free[f]];
                }
            }

            var local = svdLeft2(block);
            var scale = local.S.length ? local.S[0] : 0;
            if (scale < 1e-9) continue;
            var significant = 0;
            for (var s = 0; s < local.S.length; s++) if (local.S[s] > 1e-7 * scale) significant++;
            if (significant !== 1) continue;              // 2 means the whole plane

            var dir = local.u1;
            var matched = null;
            for (var g = 0; g < groups.length; g++) {
                if (Math.abs(groups[g].dir[0] * dir[0] + groups[g].dir[1] * dir[1]) > 1 - 1e-6) {
                    matched = groups[g];
                    break;
                }
            }
            if (matched) matched.members.push(i);
            else groups.push({ dir: dir, members: [i] });
        }
        return groups;
    }

    /* --- per-frame ------------------------------------------------------ */

    /**
     * The harmonic reference and its rate.                     HexagonDemo.jl:384
     *
     * Both come from the same solve. The harmonic extension is linear in the boundary data
     * for a fixed topology, so feeding it the target's *velocity* returns the reference's
     * velocity — an exact feedforward, not a finite difference. Note the homogeneous slot is
     * 1.0 in the position problem and 0.0 in the rate problem: the affine gauge is a
     * constant, so it has no rate, and a 1.0 there would inject a spurious dilation into
     * every agent's feedforward.
     *
     * When the observations do not determine the formation the solve returns a
     * representative of the solution set, and that representative is not the one we want —
     * with every agent at rank 0 it is the formation collapsed onto the origin. So we slide
     * along the free directions to the point nearest the configuration the agents already
     * hold: undetermined means "stay where you are", not "jump somewhere arbitrary".
     */
    function harmonicReference() {
        var n = state.offsets.length;
        if (n === 0) return;

        var buf = state.buffers;
        var N = state.nullSpace;
        var i;

        buf.boundary[0] = state.target[0];
        buf.boundary[1] = state.target[1];
        buf.boundary[2] = 1;
        matvec(state.LIB, buf.boundary, buf.rhs);
        for (i = 0; i < buf.rhs.length; i++) buf.rhs[i] = -buf.rhs[i];
        pinvSolve(state.factors, buf.rhs, buf.position, buf.solveScratch);

        buf.boundary[0] = state.velocity[0];
        buf.boundary[1] = state.velocity[1];
        buf.boundary[2] = 0;
        matvec(state.LIB, buf.boundary, buf.rhs);
        for (i = 0; i < buf.rhs.length; i++) buf.rhs[i] = -buf.rhs[i];
        pinvSolve(state.factors, buf.rhs, buf.rate, buf.solveScratch);

        if (N.cols > 0) {
            for (i = 0; i < n; i++) {
                buf.current[D * i] = state.positions[i][0];
                buf.current[D * i + 1] = state.positions[i][1];
                buf.current[D * i + 2] = 1;
            }
            for (i = 0; i < buf.delta.length; i++) buf.delta[i] = buf.current[i] - buf.position[i];
            addProjection(N, buf.delta, buf.position, buf.nullScratch, 1);
            addProjection(N, buf.rate, buf.rate, buf.nullScratch, -1);
        }
    }

    /**
     * Advance the demo by `dt` seconds.                        HexagonDemo.jl:347
     *
     * The target integrates the current command; the agents descend onto the harmonic
     * reference, with the reference's own velocity fed forward in proportion to
     * `feedforward`. Both integrators are forward Euler, as in the Julia — the caller is
     * responsible for handing this a fixed `dt`.
     */
    function step(dt) {
        state.time += dt;

        var vx = state.velocity[0], vy = state.velocity[1];
        vx += dt * (TARGET_ACCELERATION * state.command[0] - TARGET_DAMPING * vx);
        vy += dt * (TARGET_ACCELERATION * state.command[1] - TARGET_DAMPING * vy);
        var speed = Math.hypot(vx, vy);
        if (speed > TARGET_MAX_SPEED) {
            var trim = TARGET_MAX_SPEED / speed;
            vx *= trim; vy *= trim;
        }
        state.velocity[0] = vx;
        state.velocity[1] = vy;
        state.target[0] += dt * vx;
        state.target[1] += dt * vy;
        clampToArena();

        var n = state.offsets.length;
        if (n > 0) {
            harmonicReference();
            var buf = state.buffers;
            for (var i = 0; i < n; i++) {
                var refX = buf.position[D * i], refY = buf.position[D * i + 1];
                state.reference[i][0] = refX;
                state.reference[i][1] = refY;

                var cx = state.gain * (refX - state.positions[i][0]) +
                         state.feedforward * buf.rate[D * i];
                var cy = state.gain * (refY - state.positions[i][1]) +
                         state.feedforward * buf.rate[D * i + 1];
                var magnitude = Math.hypot(cx, cy);
                if (magnitude > AGENT_MAX_SPEED) {
                    var clip = AGENT_MAX_SPEED / magnitude;
                    cx *= clip; cy *= clip;
                }
                state.positions[i][0] += dt * cx;
                state.positions[i][1] += dt * cy;
            }
        }

        return state;
    }

    function clampToArena() {
        var limits = [ARENA_X / 2 - 1.2 * state.radius, ARENA_Y / 2 - 1.2 * state.radius];
        for (var axis = 0; axis < 2; axis++) {
            if (Math.abs(state.target[axis]) > limits[axis]) {
                state.target[axis] = Math.max(-limits[axis], Math.min(limits[axis], state.target[axis]));
                state.velocity[axis] = 0;
            }
        }
    }

    /* --- mutators -------------------------------------------------------- */

    // Out-of-range entries are clamped rather than rejected: this is driven by a keyboard and
    // a mouse, and a stray input should not kill the session.
    function setRanks(ranks) {
        if (ranks.length !== state.offsets.length) return;
        state.ranks = ranks.map(function (r) { return Math.max(0, Math.min(MAX_RANK, r | 0)); });
        rebuild();
    }

    function cycleRank(agent) {
        if (!(agent >= 0 && agent < state.offsets.length)) return;
        var ranks = state.ranks.slice();
        ranks[agent] = (ranks[agent] + 1) % (MAX_RANK + 1);
        setRanks(ranks);
    }

    function connectAgents(a, b) {
        var n = state.offsets.length;
        if (!(a >= 0 && a < n && b >= 0 && b < n && a !== b)) return;
        if (state.edges.length >= MAX_EDGES) return;
        var edge = normaliseEdge(a, b);
        if (findEdge(edge) >= 0) return;
        state.edges.push(edge);
        rebuild();
    }

    // Cutting edges is as consequential as lowering an observation rank, and shows up the
    // same way: a cycle survives one cut as a path, but a second cut splits the fleet into
    // halves free to drift apart, and the extra freedom appears as null-space columns.
    function disconnectAgents(a, b) {
        var index = findEdge(normaliseEdge(a, b));
        if (index < 0) return;
        state.edges.splice(index, 1);
        rebuild();
    }

    function findEdge(edge) {
        for (var i = 0; i < state.edges.length; i++) {
            var e = normaliseEdge(state.edges[i][0], state.edges[i][1]);
            if (e[0] === edge[0] && e[1] === edge[1]) return i;
        }
        return -1;
    }

    /**
     * Place a new agent, in world coordinates.                 HexagonDemo.jl:202
     *
     * Its *offset* — its share of the formation's shape — is taken relative to the target, so
     * the agent settles exactly where it was dropped and travels with the target from there.
     * It joins the end of the cyclic order, which is what defines its angle bisector, and
     * starts at rank 0 with no wiring: a new agent sees nothing and talks to no one until you
     * say otherwise.
     */
    function addNode(position) {
        if (state.offsets.length >= MAX_AGENTS) return;
        state.offsets.push([position[0] - state.target[0], position[1] - state.target[1]]);
        state.ranks.push(0);
        state.positions.push([position[0], position[1]]);
        state.reference.push([position[0], position[1]]);
        rebuild();
    }

    // The agents after it shift down to close the gap, so surviving edges are renumbered to
    // match — and because the cyclic order *is* the index order, deleting a node also re-cuts
    // its neighbours' angle bisectors.
    function removeNode(agent) {
        var n = state.offsets.length;
        if (!(agent >= 0 && agent < n)) return;
        state.offsets.splice(agent, 1);
        state.ranks.splice(agent, 1);
        state.positions.splice(agent, 1);
        state.reference.splice(agent, 1);
        state.edges = state.edges
            .filter(function (e) { return e[0] !== agent && e[1] !== agent; })
            .map(function (e) {
                return [e[0] > agent ? e[0] - 1 : e[0], e[1] > agent ? e[1] - 1 : e[1]];
            });
        rebuild();
    }

    function clearNodes() {
        state.offsets = [];
        state.ranks = [];
        state.positions = [];
        state.reference = [];
        state.edges = [];
        rebuild();
    }

    function adjustGain(factor) {
        state.gain = Math.max(GAIN_MIN, Math.min(GAIN_MAX, state.gain * factor));
        return state.gain;
    }

    // 0 → 0.5 → 1 → 0. At 1.0 the reference's own velocity is fed forward in full and the
    // tracking lag vanishes; at 0 the lag is speed / gain.
    function cycleFeedforward() {
        var index = -1;
        for (var i = 0; i < FEEDFORWARD_STEPS.length; i++) {
            if (Math.abs(FEEDFORWARD_STEPS[i] - state.feedforward) < 1e-9) { index = i; break; }
        }
        state.feedforward = FEEDFORWARD_STEPS[(index + 1) % FEEDFORWARD_STEPS.length];
        return state.feedforward;
    }

    function setCommand(command) {
        state.command[0] = command[0];
        state.command[1] = command[1];
    }

    /**
     * Return the target to the origin and clear the board.
     *
     * The demo opens on an empty board rather than a ready-made hexagon: the formation is
     * something you draw, and a ring already sitting there answers the question before it has
     * been asked. Click to place agents, drag between them to wire, and the readouts fill in
     * as the structure appears.
     */
    function reset() {
        state.target = [0, 0];
        state.velocity = [0, 0];
        state.command = [0, 0];
        state.time = 0;
        state.offsets = [];
        state.ranks = [];
        state.edges = [];
        state.positions = [];
        state.reference = [];
        rebuild();
    }

    /* --- readout --------------------------------------------------------- */

    /**
     * The frame the renderer draws: everything it needs and nothing else.
     *
     * `nullDirections` is empty exactly when the observations determine the formation; each
     * entry is a uniform translation the formation could undergo at no Dirichlet-energy cost.
     */
    function snapshot() {
        var n = state.offsets.length;
        var observers = [], directions = [], projections = [];

        for (var i = 0; i < n; i++) {
            if (state.ranks[i] === 0) continue;
            var u = state.directions[i], anchor = state.positions[i];
            var along = (state.target[0] - anchor[0]) * u[0] + (state.target[1] - anchor[1]) * u[1];
            observers.push(i);
            directions.push(u);
            projections.push([anchor[0] + along * u[0], anchor[1] + along * u[1]]);
        }

        var bars = state.barGroups.map(function (group) {
            var sx = 0, sy = 0;
            for (var k = 0; k < group.members.length; k++) {
                sx += state.positions[group.members[k]][0];
                sy += state.positions[group.members[k]][1];
            }
            return { at: [sx / group.members.length, sy / group.members.length], dir: group.dir };
        });

        var lag = 0;
        for (i = 0; i < n; i++) {
            lag = Math.max(lag, Math.hypot(state.reference[i][0] - state.positions[i][0],
                                           state.reference[i][1] - state.positions[i][1]));
        }

        return {
            t: roundTo(state.time, 3),
            radius: state.radius,
            arena: [ARENA_X, ARENA_Y],
            agents: state.positions,
            reference: state.reference,
            target: state.target,
            edges: state.edges,
            ranks: state.ranks,
            n_agents: n,
            max_agents: MAX_AGENTS,
            observers: observers,
            directions: directions,
            projections: projections,
            null_directions: bars,
            undetermined: state.nullSpace ? state.nullSpace.cols : 0,
            gain: roundTo(state.gain, 2),
            feedforward: state.feedforward,
            lag: roundTo(lag, 3),
            energy: energy()
        };
    }

    /**
     * Dirichlet energy of the current configuration, to the nearest 1e-4.
     *
     * Anything below that reads as zero. Once the formation has converged the residual is
     * float noise around 1e-29, and reporting it to four significant figures made a settled
     * board look busy.
     */
    function energy() {
        if (!state.sheaf) return 0;
        if (state.edges.length === 0 && state.ranks.every(function (r) { return r === 0; })) return 0;
        var value = sheafEnergy(state.sheaf, state.positions, state.target);
        return value < 1e-4 ? 0 : Math.round(value * 1e4) / 1e4;
    }

    reset();

    return {
        state: state,
        step: step,
        snapshot: snapshot,
        setCommand: setCommand,
        setRanks: setRanks,
        cycleRank: cycleRank,
        connectAgents: connectAgents,
        disconnectAgents: disconnectAgents,
        addNode: addNode,
        removeNode: removeNode,
        clearNodes: clearNodes,
        adjustGain: adjustGain,
        cycleFeedforward: cycleFeedforward,
        reset: reset,
        rebuild: rebuild
    };
}

/* ===========================================================================
 * §4 / §5 / §6  Renderer, input and lifecycle                    www/index.html
 *
 * Transplanted from the original front end. The mathematics is now local, so the WebSocket
 * boundary collapses: `send({action: …})` becomes a direct call, and the per-frame snapshot
 * that used to arrive over the wire is read straight out of the simulation.
 *
 * One deliberate index change throughout: the wire protocol was 1-based (Julia's convention)
 * and everything here is 0-based, so `state.agents[a - 1]` became `state.agents[a]`.
 * ======================================================================== */

var PALETTE_KEYS = ["--slate", "--ink", "--muted", "--heading", "--line", "--agent",
                    "--target", "--bisector", "--observer", "--full", "--ghost", "--warn"];

var AXIS_KEYS = {
    ArrowLeft: [-1, 0], KeyA: [-1, 0],
    ArrowRight: [1, 0], KeyD: [1, 0],
    ArrowUp: [0, 1], KeyW: [0, 1],
    ArrowDown: [0, -1], KeyS: [0, -1]
};

var FIXED_STEP = 1 / 60;
var DRAG_SLOP = 5;              // CSS px of movement before a press counts as a drag
var LONG_PRESS_MS = 500;
// How long the target's path lingers behind it.
//
// Counted in simulation steps rather than rendered frames, and appended inside the fixed-step
// loop below. The original pushed one point per rAF tick, which made the trail last twice as
// long on a 60 Hz display as on a 120 Hz one — a duration that quietly depended on the
// viewer's monitor.
var TRAIL_SECONDS = 2;
var TRAIL_LENGTH = Math.round(TRAIL_SECONDS * 60);

function mountDemo(rootElement, options) {
    var opts = options || {};
    var pick = function (name) { return rootElement.querySelector('[data-sheaf="' + name + '"]'); };

    var canvas = pick("view");
    if (!canvas) throw new Error('sheaf-demo: no [data-sheaf="view"] canvas inside the container');
    var ctx = canvas.getContext("2d");
    var statusEl = pick("status");
    var stickEl = pick("stick");
    var knobEl = pick("knob");
    var actionsEl = pick("actions");

    var out = {};
    ["obs", "nullity", "lag", "gains", "energy"].forEach(function (key) {
        out[key] = pick(key);
    });

    // Read once. The original called getComputedStyle inside the render loop, roughly fifteen
    // times a frame — a forced style recalculation each time, which is invisible on a laptop
    // and very much not on a phone.
    var palette = {};
    var computed = rootElement.ownerDocument.defaultView.getComputedStyle(rootElement);
    PALETTE_KEYS.forEach(function (key) {
        palette[key] = computed.getPropertyValue(key).trim() || "#ffffff";
    });
    var color = function (key) { return palette[key]; };

    var coarsePointer = rootElement.ownerDocument.defaultView.matchMedia &&
        rootElement.ownerDocument.defaultView.matchMedia("(pointer: coarse)").matches;

    var sim = createSimulation();
    var frame = sim.snapshot();
    var trail = [];
    var held = new Set();
    var viewHalf = null;
    var running = true;
    var rafHandle = null;
    var lastTime = null;
    var accumulator = 0;
    var listeners = [];

    var dragFrom = null;        // agent index a drag started on
    var dragPoint = null;       // where the pointer is now, in world units
    var hoverEdge = null;       // index into state.edges, for highlight and cursor feedback
    var pressHandled = false;   // the press already did its job; pointerup must not act again
    var pressAt = null;         // where the press landed, in CSS px, to tell a click from a drag
    var longPressTimer = null;
    var stickPointer = null;
    var stickCommand = [0, 0];

    function on(target, type, handler, options) {
        target.addEventListener(type, handler, options);
        listeners.push([target, type, handler, options]);
    }

    function setStatus(text, bad) {
        if (!statusEl) return;
        statusEl.textContent = text;
        statusEl.classList.toggle("is-bad", !!bad);
    }

    /* --- the view ---------------------------------------------------------
     * The drawn region is centred on the origin, letterboxed, and *at least* the arena. It
     * has to be allowed to be more: agents go wherever you click and an agent's offset from
     * the target is fixed once placed, so driving the target to its own limit carries a
     * far-flung agent well past the arena wall. The arena only bounds the target. An agent
     * you cannot see is an agent you cannot click.
     * ------------------------------------------------------------------- */

    // Half-extents containing everything render is about to draw. Only markers count: the
    // bisector construction lines run off past the edge by design.
    function contentHalf(state) {
        var hw = state.arena[0] / 2, hh = state.arena[1] / 2;
        var margin = 0.2 * state.radius;
        // A non-finite coordinate would otherwise poison the scale and blank the whole canvas
        // rather than losing the one marker it belongs to.
        function see(p) {
            if (!Number.isFinite(p[0]) || !Number.isFinite(p[1])) return;
            hw = Math.max(hw, Math.abs(p[0]) + margin);
            hh = Math.max(hh, Math.abs(p[1]) + margin);
        }
        state.agents.forEach(see);
        state.projections.forEach(see);
        see(state.target);
        return [hw, hh];
    }

    // Grow at once, shrink slowly. Something leaving the arena must be visible on the very
    // frame it does so, but the board should not twitch each time an agent brushes the wall.
    function updateView(state) {
        var want = contentHalf(state);
        viewHalf = viewHalf === null ? want
            : [Math.max(want[0], viewHalf[0] + (want[0] - viewHalf[0]) * 0.05),
               Math.max(want[1], viewHalf[1] + (want[1] - viewHalf[1]) * 0.05)];
        return viewHalf;
    }

    function makeTransform(half) {
        var scale = Math.min(canvas.width / (2 * half[0]), canvas.height / (2 * half[1]));
        var project = function (p) {
            return [canvas.width / 2 + p[0] * scale, canvas.height / 2 - p[1] * scale];
        };
        project.scale = scale;
        return project;
    }

    // Match the backing store to the element's device pixels so the drawing stays sharp at any
    // size. The ratio is capped at 2: a 3x phone at full screen is 5.4 Mpx of fill for no
    // visible gain. makeTransform letterboxes, so the canvas can be any aspect ratio.
    function fitCanvas() {
        var box = canvas.getBoundingClientRect();
        if (box.width === 0 || box.height === 0) return;      // still off-screen
        var dpr = Math.min(rootElement.ownerDocument.defaultView.devicePixelRatio || 1, 2);
        canvas.width = Math.max(1, Math.round(box.width * dpr));
        canvas.height = Math.max(1, Math.round(box.height * dpr));
        render(frame);
    }

    /* --- editing the consensus topology --------------------------------- */

    // Pointer position in world units. The backing store is in device pixels while the event
    // is in CSS pixels, so the ratio between them has to come out. Read through the same view
    // the last frame was drawn with, so what you click is what you saw.
    function pointerWorld(event) {
        if (!frame) return null;
        var box = canvas.getBoundingClientRect();
        if (box.width === 0 || box.height === 0) return null;
        var px = (event.clientX - box.left) * (canvas.width / box.width);
        var py = (event.clientY - box.top) * (canvas.height / box.height);
        var scale = makeTransform(viewHalf || contentHalf(frame)).scale;
        return [(px - canvas.width / 2) / scale, (canvas.height / 2 - py) / scale];
    }

    // Grab radius around an agent. This has to stay well under half an edge length: a regular
    // hexagon's side equals its circumradius, so a reach of 0.5 would have the two endpoint
    // discs meet in the middle and leave no part of any ring edge clickable at all. At 0.16
    // the grab zone is about four times the drawn marker and the middle ~70% of each edge
    // stays free for cutting. Under a coarse pointer both reaches are enlarged: at the default
    // view 0.16 works out to roughly eight CSS pixels on a phone, against the site's own
    // declared 44 px minimum touch target.
    function agentReach() { return (coarsePointer ? 0.28 : 0.16) * frame.radius; }
    function edgeReach() { return (coarsePointer ? 0.22 : 0.13) * frame.radius; }

    function agentAt(world) {
        if (!frame || !world) return null;
        var best = null, bestDistance = agentReach();
        frame.agents.forEach(function (p, i) {
            var distance = Math.hypot(p[0] - world[0], p[1] - world[1]);
            if (distance < bestDistance) { best = i; bestDistance = distance; }
        });
        return best;
    }

    function edgeAt(world) {
        if (!frame || !world) return null;
        var best = null, bestDistance = edgeReach();
        frame.edges.forEach(function (edge, k) {
            var p = frame.agents[edge[0]], q = frame.agents[edge[1]];
            if (!p || !q) return;
            var vx = q[0] - p[0], vy = q[1] - p[1];
            var len2 = vx * vx + vy * vy;
            // Distance to the segment, not to the infinite line.
            var t = len2 === 0 ? 0 : Math.max(0, Math.min(1,
                ((world[0] - p[0]) * vx + (world[1] - p[1]) * vy) / len2));
            var distance = Math.hypot(p[0] + t * vx - world[0], p[1] + t * vy - world[1]);
            if (distance < bestDistance) { best = k; bestDistance = distance; }
        });
        return best;
    }

    function cancelLongPress() {
        if (longPressTimer !== null) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
        }
    }

    on(canvas, "pointerdown", function (event) {
        var world = pointerWorld(event);
        var agent = agentAt(world);
        pressHandled = false;
        pressAt = [event.clientX, event.clientY];
        cancelLongPress();
        if (agent === null) return;

        // Without this the release would fall through to the edge/board logic below and,
        // since an agent sits on the end of its own edges, immediately cut one of them too.
        if (event.shiftKey) {
            pressHandled = true;
            sim.removeNode(agent);
            return;
        }
        // Shift-click has no touch equivalent, so a long press stands in for it.
        if (event.pointerType !== "mouse") {
            longPressTimer = setTimeout(function () {
                longPressTimer = null;
                pressHandled = true;
                dragFrom = null;
                dragPoint = null;
                sim.removeNode(agent);
            }, LONG_PRESS_MS);
        }
        dragFrom = agent;
        dragPoint = world;
        canvas.setPointerCapture(event.pointerId);
        event.preventDefault();
    });

    on(canvas, "pointermove", function (event) {
        var world = pointerWorld(event);
        if (pressAt && Math.hypot(event.clientX - pressAt[0], event.clientY - pressAt[1]) > DRAG_SLOP) {
            cancelLongPress();
        }
        if (dragFrom !== null) {
            dragPoint = world;
            canvas.style.cursor = "grabbing";
            return;
        }
        var over = agentAt(world);
        hoverEdge = over === null ? edgeAt(world) : null;
        canvas.style.cursor =
            over !== null ? (event.shiftKey ? "not-allowed" : "grab")
            : hoverEdge !== null ? "pointer"
            : (frame && frame.n_agents < frame.max_agents) ? "copy" : "default";
    });

    on(canvas, "pointerup", function (event) {
        cancelLongPress();
        if (pressHandled) { pressHandled = false; dragFrom = null; dragPoint = null; return; }
        var world = pointerWorld(event);
        // Click or drag is decided by whether the pointer actually moved, not by what happened
        // to be under it when pressed. Agents are freely placed, so one can sit right on top
        // of somebody else's edge — as agent 2 can end up doing to edge 1-6 — and if merely
        // pressing near an agent claimed the gesture, that edge would be uncuttable through no
        // fault of the user's aim.
        var moved = pressAt !== null &&
            Math.hypot(event.clientX - pressAt[0], event.clientY - pressAt[1]) > DRAG_SLOP;

        if (dragFrom !== null) {
            var from = dragFrom;
            var landed = agentAt(world);
            dragFrom = null;
            dragPoint = null;
            canvas.style.cursor = "default";
            if (moved && landed !== null && landed !== from) {
                sim.connectAgents(from, landed);
                return;
            }
            // A tap on an agent that never moved. On a desktop this falls through to the
            // cut/add logic below, as the original did. On a touch device there are no number
            // keys, so tapping an agent is the only way to cycle its rank — and it is much the
            // more useful of the two readings of the gesture there.
            if (!moved && coarsePointer && landed !== null) {
                sim.cycleRank(from);
                return;
            }
        }

        // A plain click cuts an edge, or drops a new agent on empty board.
        var k = edgeAt(world);
        if (k !== null && frame && frame.edges[k]) {
            sim.disconnectAgents(frame.edges[k][0], frame.edges[k][1]);
            hoverEdge = null;
            return;
        }
        if (world && frame && frame.n_agents < frame.max_agents) sim.addNode(world);
    });

    on(canvas, "pointerleave", function () {
        cancelLongPress();
        hoverEdge = null;
        canvas.style.cursor = "default";
    });

    on(canvas, "pointercancel", function () {
        cancelLongPress();
        dragFrom = null;
        dragPoint = null;
    });

    /* --- keyboard -------------------------------------------------------- */

    function commandFromKeys() {
        var x = 0, y = 0;
        held.forEach(function (code) {
            var axis = AXIS_KEYS[code];
            if (axis) { x += axis[0]; y += axis[1]; }
        });
        var norm = Math.hypot(x, y) || 1;
        return [x / norm, y / norm];
    }

    function applyCommand() {
        var keys = commandFromKeys();
        // Whichever input is actually being used wins; they are never both live.
        sim.setCommand(keys[0] || keys[1] ? keys : stickCommand);
    }

    function typingInto(target) {
        if (!target || !target.tagName) return false;
        var tag = target.tagName.toLowerCase();
        return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
    }

    var view = rootElement.ownerDocument.defaultView;

    on(view, "keydown", function (event) {
        // These listeners live on a real website now, not a localhost toy. Modifier chords
        // belong to the browser and the OS, never to the demo.
        if (event.metaKey || event.ctrlKey || event.altKey) return;
        if (typingInto(event.target)) return;
        // A panel mid-close is still mounted for another 450ms; it must not eat keys.
        if (opts.isActive && !opts.isActive()) return;

        if (event.code === "Escape") {
            if (opts.onClose) { event.preventDefault(); opts.onClose(); }
            return;
        }
        if (AXIS_KEYS[event.code]) {
            event.preventDefault();
            if (!held.has(event.code)) { held.add(event.code); applyCommand(); }
            return;
        }
        if (event.code === "Space") { event.preventDefault(); doAction("reset"); return; }
        // Not "S": that is already WASD's down key.
        if (event.code === "KeyF") { doAction("feedforward"); return; }
        if (event.code === "BracketLeft") { doAction("gain-down"); return; }
        if (event.code === "BracketRight") { doAction("gain-up"); return; }
        if (event.code === "KeyC") { doAction("clear-nodes"); return; }

        var digit = /^Digit([1-6])$/.exec(event.code);
        if (digit) sim.cycleRank(Number(digit[1]) - 1);
    });

    on(view, "keyup", function (event) {
        if (held.delete(event.code)) applyCommand();
    });
    on(view, "blur", function () { held.clear(); applyCommand(); });

    /* --- discrete actions, shared by the keyboard and the touch buttons --- */

    function doAction(name) {
        switch (name) {
            case "reset": trail = []; sim.reset(); break;
            case "feedforward": sim.cycleFeedforward(); break;
            case "gain-down": sim.adjustGain(1 / 1.25); break;
            case "gain-up": sim.adjustGain(1.25); break;
            case "clear-nodes": sim.clearNodes(); break;
        }
    }

    if (actionsEl) {
        on(actionsEl, "click", function (event) {
            var button = event.target.closest("[data-action]");
            if (button) doAction(button.getAttribute("data-action"));
        });
    }

    /* --- the virtual thumbstick ------------------------------------------
     * A phone has no arrow keys, so without this the target simply cannot be driven and every
     * readout sits frozen. It feeds the same normalised command vector the keys produce, so
     * the acceleration, damping and speed cap stay exactly as they are — teleporting the
     * target instead would have thrown all three away.
     * ------------------------------------------------------------------- */

    function stickRadius() {
        var box = stickEl.getBoundingClientRect();
        return Math.max(1, Math.min(box.width, box.height) / 2);
    }

    function updateStick(event) {
        var box = stickEl.getBoundingClientRect();
        var dx = event.clientX - (box.left + box.width / 2);
        var dy = event.clientY - (box.top + box.height / 2);
        var radius = stickRadius();
        var distance = Math.hypot(dx, dy);
        var clipped = distance > radius ? radius / distance : 1;
        var kx = dx * clipped, ky = dy * clipped;

        if (knobEl) knobEl.style.transform = "translate(" + kx + "px, " + ky + "px)";
        // A short throw should still mean full speed in that direction: this is a direction
        // control, exactly like the keys, not a proportional throttle.
        var norm = Math.hypot(kx, ky);
        stickCommand = norm < radius * 0.18 ? [0, 0] : [kx / norm, -ky / norm];
        applyCommand();
    }

    function releaseStick() {
        stickPointer = null;
        stickCommand = [0, 0];
        if (knobEl) knobEl.style.transform = "";
        if (stickEl) stickEl.classList.remove("is-live");
        applyCommand();
    }

    if (stickEl) {
        on(stickEl, "pointerdown", function (event) {
            stickPointer = event.pointerId;
            stickEl.setPointerCapture(event.pointerId);
            stickEl.classList.add("is-live");
            event.preventDefault();
            updateStick(event);
        });
        on(stickEl, "pointermove", function (event) {
            if (stickPointer === event.pointerId) updateStick(event);
        });
        on(stickEl, "pointerup", function (event) {
            if (stickPointer === event.pointerId) releaseStick();
        });
        on(stickEl, "pointercancel", releaseStick);
    }

    /* --- drawing ---------------------------------------------------------- */

    function line(a, b, stroke, width, dash) {
        ctx.save();
        ctx.strokeStyle = stroke;
        ctx.lineWidth = width;
        ctx.setLineDash(dash || []);
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(b[0], b[1]);
        ctx.stroke();
        ctx.restore();
    }

    function disc(p, radius, fill, stroke, width) {
        ctx.beginPath();
        ctx.arc(p[0], p[1], radius, 0, 2 * Math.PI);
        if (fill) { ctx.fillStyle = fill; ctx.fill(); }
        if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
    }

    function render(state) {
        if (!state) return;
        var half = updateView(state);
        var toPixels = makeTransform(half);
        // Every visual size below is a fraction of `u`, the ring radius in pixels, so the
        // drawing keeps its proportions at any window size or pixel density.
        var u = toPixels.scale * state.radius;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Each bar is a translation the formation can make for free, drawn through the
        // centroid of the agents it actually moves. Modes that are not translations get no
        // bar — see computeBarGroups.
        if (state.null_directions.length > 0) {
            ctx.save();
            ctx.globalAlpha = 0.3;
            state.null_directions.forEach(function (bar) {
                var reach = 0.84 * half[0];
                line(toPixels([bar.at[0] - bar.dir[0] * reach, bar.at[1] - bar.dir[1] * reach]),
                     toPixels([bar.at[0] + bar.dir[0] * reach, bar.at[1] + bar.dir[1] * reach]),
                     color("--warn"), 0.070 * u);
            });
            ctx.restore();
        }

        // Bisector lines, only for the rank-1 agents: a rank-2 agent is not confined to a
        // line, and a rank-0 agent sees nothing to draw.
        state.observers.forEach(function (agent, k) {
            if (state.ranks[agent] !== 1) return;
            var d = state.directions[k];
            var anchor = state.agents[agent];
            var reach = 2.8 * half[0];
            // Held well back: these are construction lines, and at full strength Pi Mile
            // competes with the white target for attention.
            ctx.save();
            ctx.globalAlpha = 0.4;
            line(toPixels([anchor[0] - d[0] * reach, anchor[1] - d[1] * reach]),
                 toPixels([anchor[0] + d[0] * reach, anchor[1] + d[1] * reach]),
                 color("--bisector"), 0.0097 * u, [0.046 * u, 0.039 * u]);
            ctx.restore();
        });

        if (trail.length > 1) {
            ctx.save();
            ctx.strokeStyle = color("--ink");
            ctx.globalAlpha = 0.22;
            ctx.lineWidth = 0.0097 * u;
            ctx.beginPath();
            trail.forEach(function (p, i) {
                var q = toPixels(p);
                if (i === 0) ctx.moveTo(q[0], q[1]); else ctx.lineTo(q[0], q[1]);
            });
            ctx.stroke();
            ctx.restore();
        }

        // Consensus edges: the fixed-displacement constraints. Editable, so the one under the
        // cursor lights up.
        state.edges.forEach(function (edge, k) {
            var hot = hoverEdge === k;
            line(toPixels(state.agents[edge[0]]), toPixels(state.agents[edge[1]]),
                 hot ? color("--warn") : color("--agent"), (hot ? 0.032 : 0.0155) * u);
        });

        // An edge being dragged into existence.
        if (dragFrom !== null && dragPoint !== null && state.agents[dragFrom]) {
            line(toPixels(state.agents[dragFrom]), toPixels(dragPoint),
                 color("--ghost"), 0.022 * u, [0.09 * u, 0.07 * u]);
        }

        // What each observer actually measures. A rank-1 agent gets the target's foot on its
        // bisector — one number. A rank-2 agent gets the target itself, drawn as a solid sight
        // line straight to it.
        state.observers.forEach(function (agent, k) {
            var rank = state.ranks[agent];
            if (rank === 1) {
                var foot = state.projections[k];
                line(toPixels(state.target), toPixels(foot), color("--observer"),
                     0.0097 * u, [0.027 * u, 0.027 * u]);
                disc(toPixels(foot), 0.031 * u, color("--observer"));
            } else if (rank === 2) {
                line(toPixels(state.agents[agent]), toPixels(state.target), color("--full"), 0.0097 * u);
            }
        });

        // Agents, ringed by rank: rank 1 in the projection colour, rank 2 in the full-sight
        // colour, rank 0 bare.
        state.agents.forEach(function (p, i) {
            var rank = state.ranks[i];
            var ring = rank === 1 ? color("--observer") : rank === 2 ? color("--full") : null;
            disc(toPixels(p), 0.077 * u, color("--agent"), ring, 0.023 * u);
            var q = toPixels(p);
            ctx.fillStyle = "#ffffff";
            ctx.font = "600 " + (0.085 * u) + "px ui-sans-serif, system-ui, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(String(i + 1), q[0], q[1] + 0.004 * u);
        });

        var target = toPixels(state.target);
        ctx.save();
        ctx.fillStyle = color("--target");
        ctx.strokeStyle = color("--ink");
        ctx.lineWidth = 0.016 * u;
        ctx.beginPath();
        for (var k = 0; k < 10; k++) {
            var radius = (k % 2 === 0 ? 0.085 : 0.035) * u;
            var angle = (Math.PI / 5) * k - Math.PI / 2;
            var point = [target[0] + radius * Math.cos(angle), target[1] + radius * Math.sin(angle)];
            if (k === 0) ctx.moveTo(point[0], point[1]); else ctx.lineTo(point[0], point[1]);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.restore();

        writeReadout(state);
    }

    function writeReadout(state) {
        if (out.obs) out.obs.textContent = state.ranks.length ? state.ranks.join("·") : "—";
        if (out.nullity) {
            out.nullity.textContent = String(state.undetermined);
            out.nullity.classList.toggle("is-warn", state.undetermined > 0);
        }
        if (out.lag) out.lag.textContent = Number(state.lag).toFixed(2);
        if (out.gains) {
            out.gains.textContent = Number(state.gain).toFixed(1) + " / " + Number(state.feedforward);
        }
        // Four decimals, or a bare 0 — "0.0000" reads as a measurement, and this is an exact
        // zero by the reporting threshold rather than a small number.
        if (out.energy) {
            out.energy.textContent = state.energy === 0 ? "0" : state.energy.toFixed(4);
        }
    }

    /* --- the frame loop ---------------------------------------------------
     * server.jl owned its own clock and stepped a constant 1/60. requestAnimationFrame does
     * not: it is 120 Hz on a ProMotion display, and a backgrounded tab hands back a
     * multi-second delta that would blow a forward-Euler integrator apart on the first frame
     * after refocus. A fixed-step accumulator keeps the dynamics frame-rate independent and
     * reproduces the Julia numbers exactly, so a 120 Hz laptop and a 60 Hz one show the same
     * formation rather than two different gains' worth of lag.
     * ------------------------------------------------------------------- */

    function tick(now) {
        if (!running) return;
        rafHandle = requestAnimationFrame(tick);
        try {
            var seconds = now / 1000;
            if (lastTime === null) lastTime = seconds;
            accumulator += Math.min(seconds - lastTime, 0.25);
            lastTime = seconds;

            var steps = 0;
            while (accumulator >= FIXED_STEP && steps < 5) {
                sim.step(FIXED_STEP);
                // One point per simulated step, not per rendered frame, so the trail covers
                // the same span of time whatever the display is doing.
                trail.push([sim.state.target[0], sim.state.target[1]]);
                accumulator -= FIXED_STEP;
                steps++;
            }
            if (steps === 0) return;                       // nothing moved; nothing to redraw
            if (trail.length > TRAIL_LENGTH) trail.splice(0, trail.length - TRAIL_LENGTH);

            frame = sim.snapshot();
            render(frame);
        } catch (err) {
            // A throw here would otherwise repeat sixty times a second. Stop once, say so.
            running = false;
            setStatus("the demo hit an error and stopped — reload to try again", true);
            if (root.console) root.console.error("sheaf-demo:", err);
        }
    }

    var resizeObserver = null;
    // getBoundingClientRect is zero while the panel is still off-screen, so the first frame
    // would render into a 1x1 canvas. A ResizeObserver fires when the panel gains its size and
    // covers window resizes too, which a resize listener alone would not.
    if (typeof ResizeObserver !== "undefined") {
        resizeObserver = new ResizeObserver(function () { fitCanvas(); });
        resizeObserver.observe(canvas.parentElement || canvas);
    } else {
        on(view, "resize", fitCanvas);
    }

    // The status line carries errors only; there is no idle message. The key and mouse tables
    // in the sidebar already say how to drive the thing.
    fitCanvas();
    rafHandle = requestAnimationFrame(tick);

    return {
        simulation: sim,
        resize: fitCanvas,
        // Reopening a lazily-mounted panel without a clean teardown leaves two frame loops
        // racing on one canvas, which is the classic version of this bug.
        unmount: function () {
            running = false;
            if (rafHandle !== null) cancelAnimationFrame(rafHandle);
            cancelLongPress();
            listeners.forEach(function (entry) {
                entry[0].removeEventListener(entry[1], entry[2], entry[3]);
            });
            listeners = [];
            if (resizeObserver) resizeObserver.disconnect();
            held.clear();
            trail = [];
            frame = null;
        }
    };
}

/* ===========================================================================
 * Exports
 * ======================================================================== */

// One mounted instance at a time. The panel is lazily loaded and can be reopened, so this is
// what keeps a second frame loop from being started on top of the first.
var current = null;

root.SheafDemo = {
    /**
     * Start the demo inside `container`, which must hold a [data-sheaf="view"] canvas.
     *
     * options.onClose  — called when the user presses Escape
     * options.isActive — consulted before handling a key, so a hidden panel stays inert
     */
    mount: function (container, options) {
        if (current) current.unmount();
        current = mountDemo(container, options);
        return current;
    },

    unmount: function () {
        if (!current) return;
        current.unmount();
        current = null;
    },

    resize: function () { if (current) current.resize(); },

    isMounted: function () { return current !== null; },

    createSimulation: createSimulation,
    constants: {
        MAX_AGENTS: MAX_AGENTS, MAX_EDGES: MAX_EDGES, RADIUS: RADIUS, D: D, MAX_RANK: MAX_RANK,
        ARENA_X: ARENA_X, ARENA_Y: ARENA_Y,
        TARGET_ACCELERATION: TARGET_ACCELERATION, TARGET_DAMPING: TARGET_DAMPING,
        TARGET_MAX_SPEED: TARGET_MAX_SPEED, AGENT_MAX_SPEED: AGENT_MAX_SPEED,
        DEFAULT_GAIN: DEFAULT_GAIN, FEEDFORWARD_STEPS: FEEDFORWARD_STEPS
    },
    // Exposed for the Node self-test in tests/js/. Not part of the page's API.
    _internals: {
        mat: mat, matFrom: matFrom, identity: identity, transpose: transpose,
        matmul: matmul, matTmul: matTmul, matvec: matvec,
        svdTall: svdTall, svdLeft2: svdLeft2, nullBasis: nullBasis, pinvSolve: pinvSolve,
        affineFrame: affineFrame, observationSelector: observationSelector,
        bisectorDirections: bisectorDirections, buildSheaf: buildSheaf,
        assembleBlocks: assembleBlocks, harmonicExtension: harmonicExtension,
        sheafEnergy: sheafEnergy,
        regularOffsets: regularOffsets, normaliseEdge: normaliseEdge
    }
};

})(typeof globalThis !== "undefined" ? globalThis : this);

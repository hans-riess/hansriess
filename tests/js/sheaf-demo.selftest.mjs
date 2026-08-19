/*
 * Numerical self-test for the coordination sheaf port in static/js/sheaf-demo.js.
 *
 *     node tests/js/sheaf-demo.selftest.mjs
 *
 * Needs no browser, no Django and no database — sheaf-demo.js touches the DOM only inside
 * mount(), so the mathematics loads and runs headless.
 *
 * hexagon_reference.json, exported from the Julia by docs/scripts/export_hexagon_golden.jl,
 * is checked when present but deliberately does not carry this suite. Its configuration has
 * nullity 0, so the answer reduces to q[i] = target + radius·[cos((i−1)π/3), sin((i−1)π/3)]:
 * it pins down sheaf assembly and a well-posed solve, and exercises none of the null-space
 * projection, the rate solve, the translation bars or edge editing. Everything below tests
 * an invariant instead — a fact about the construction that holds independently of how
 * either implementation is written.
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const DEMO = join(HERE, "..", "..", "static", "js", "sheaf-demo.js");

// sheaf-demo.js is a classic script, not a module (in production it is served cross-origin
// from S3, where module scripts would be blocked by CORS). Evaluating it in global scope is
// exactly what a <script> tag does.
new Function(readFileSync(DEMO, "utf8"))();

const { createSimulation, constants, _internals: X } = globalThis.SheafDemo;
const { D } = constants;

/* --- harness ---------------------------------------------------------- */

let passed = 0;
const failures = [];

function test(name, fn) {
    try {
        fn();
        passed++;
        console.log(`  ok   ${name}`);
    } catch (err) {
        failures.push({ name, err });
        console.log(`  FAIL ${name}\n       ${err.message}`);
    }
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function assertClose(actual, expected, tol, what) {
    if (!(Math.abs(actual - expected) <= tol)) {
        throw new Error(`${what}: expected ${expected}, got ${actual} (tol ${tol})`);
    }
}

function assertEqual(actual, expected, what) {
    if (actual !== expected) throw new Error(`${what}: expected ${expected}, got ${actual}`);
}

function section(title) { console.log(`\n${title}`); }

/* --- fixtures --------------------------------------------------------- */

const HEX = X.regularOffsets(6, 0.55);

/**
 * The cycle (0,1), (1,2), … (n-1,0), normalised low-index-first.
 *
 * The demo no longer builds a ring for you — you wire whatever you draw — so this fixture
 * lives here rather than in the source. The normalisation matters: the wrap-around edge is
 * built as (n-1, 0), and an unordered pair would make that one edge, and only that one,
 * impossible to cut.
 */
function cycleEdges(n) {
    const out = [];
    if (n >= 3) for (let i = 0; i < n; i++) out.push(X.normaliseEdge(i, (i + 1) % n));
    else for (let j = 0; j < n - 1; j++) out.push(X.normaliseEdge(j, j + 1));
    return out;
}

const HEX_EDGES = cycleEdges(6);

function ranksFrom(observers, n = 6, rank = 1) {
    const ranks = new Array(n).fill(0);
    for (const i of observers) ranks[i] = rank;
    return ranks;
}

// Agents 1, 3, 5 at rank 1 — three readings 120 degrees apart, the configuration the
// README's tables are stated for.
const OBSERVERS_135 = ranksFrom([0, 2, 4]);

/**
 * A six-agent ring, built the way a user builds one: drop the agents, wire them up, set the
 * ranks. The demo now opens on an empty board, so every test that wants a formation has to
 * say so — which has the side benefit of exercising addNode on the way in.
 */
function hexagonSim() {
    const sim = createSimulation();
    for (const offset of HEX) sim.addNode(offset);      // target sits at the origin after reset
    for (const [a, b] of HEX_EDGES) sim.connectAgents(a, b);
    sim.setRanks(OBSERVERS_135);
    return sim;
}

function nullity(offsets, ranks, edges) {
    const sheaf = X.buildSheaf(offsets, ranks, edges);
    return X.harmonicExtension(sheaf, [0, 0, 1]).nullSpace.cols;
}

// A deterministic PRNG, so a failure is always reproducible.
function rng(seed) {
    let s = seed >>> 0;
    return () => {
        s = (s * 1664525 + 1013904223) >>> 0;
        return s / 4294967296;
    };
}

/* --- 1. the escort formation is an exact global section ---------------- */

section("1. exact global section");

/**
 * For any centre p, the configuration x_i = [p + d_i; 1], x_target = [p; 1] should have zero
 * Dirichlet energy: consensus edges see [p;1] from both sides, and observation edges see
 * S_i[p;1] from both sides. The strongest single check on sheaf assembly available without a
 * reference implementation — it catches a sign error in affineFrame, a transposed selector,
 * a missing gauge row, or a mismatched edge orientation.
 */
function sectionEnergy(offsets, ranks, edges, centre) {
    const sheaf = X.buildSheaf(offsets, ranks, edges);
    const positions = offsets.map((d) => [centre[0] + d[0], centre[1] + d[1]]);
    return X.sheafEnergy(sheaf, positions, centre);
}

test("hexagon, default ranks, at several centres", () => {
    for (const centre of [[0, 0], [1.3, -0.7], [-0.4, 2.2], [12, 9]]) {
        const energy = sectionEnergy(HEX, OBSERVERS_135, HEX_EDGES, centre);
        assert(energy < 1e-12, `centre ${centre}: energy ${energy}`);
    }
});

test("hexagon, every agent at rank 2", () => {
    const energy = sectionEnergy(HEX, new Array(6).fill(2), HEX_EDGES, [0.8, -1.1]);
    assert(energy < 1e-12, `energy ${energy}`);
});

test("irregular pentagon, mixed ranks", () => {
    const random = rng(20250819);
    const offsets = [];
    for (let i = 0; i < 5; i++) {
        const angle = (i * 2 * Math.PI) / 5 + 0.3 * (random() - 0.5);
        const radius = 0.4 + 0.6 * random();
        offsets.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
    }
    const energy = sectionEnergy(offsets, [1, 0, 2, 1, 0], cycleEdges(5), [-0.6, 0.9]);
    assert(energy < 1e-12, `energy ${energy}`);
});

test("a partial wiring is still a section", () => {
    const energy = sectionEnergy(HEX, OBSERVERS_135, [[0, 1], [2, 3], [4, 5]], [0.2, 0.2]);
    assert(energy < 1e-12, `energy ${energy}`);
});

/* --- 2. the feedforward really is the reference's derivative ----------- */

section("2. feedforward is the exact derivative");

/**
 * harmonic_extension is linear in the boundary data for a fixed topology, so feeding it the
 * target's *velocity* returns the reference's velocity. This is the only test that catches a
 * 1.0 in the homogeneous slot of the rate problem — an error that is otherwise invisible,
 * since it just makes every agent's feedforward slightly wrong.
 */
test("rate solve matches a central difference of the position solve", () => {
    const sheaf = X.buildSheaf(HEX, OBSERVERS_135, HEX_EDGES);
    const target = [0.3, -0.45];
    const velocity = [0.9, 1.4];
    const h = 1e-5;

    const forward = X.harmonicExtension(sheaf,
        [target[0] + h * velocity[0], target[1] + h * velocity[1], 1]).x;
    const back = X.harmonicExtension(sheaf,
        [target[0] - h * velocity[0], target[1] - h * velocity[1], 1]).x;
    const rate = X.harmonicExtension(sheaf, [velocity[0], velocity[1], 0]).x;

    for (let i = 0; i < rate.length; i++) {
        const difference = (forward[i] - back[i]) / (2 * h);
        assertClose(rate[i], difference, 1e-6, `dof ${i}`);
    }
});

test("a 1.0 in the rate slot would be caught", () => {
    const sheaf = X.buildSheaf(HEX, OBSERVERS_135, HEX_EDGES);
    const correct = X.harmonicExtension(sheaf, [0.9, 1.4, 0]).x;
    const wrong = X.harmonicExtension(sheaf, [0.9, 1.4, 1]).x;
    let maximum = 0;
    for (let i = 0; i < correct.length; i++) maximum = Math.max(maximum, Math.abs(correct[i] - wrong[i]));
    assert(maximum > 1e-3, `the two should differ, but the largest gap was ${maximum}`);
});

/* --- 3. the nullity table --------------------------------------------- */

section("3. nullity table (README and Formations.jl docstring)");

test("ranks, with the ring fully wired", () => {
    const cases = [
        [[1, 0, 1, 0, 1, 0], 0, "agents 1,3,5 at rank 1 — three readings 120° apart"],
        [[2, 0, 0, 0, 0, 0], 0, "one agent at rank 2 — two readings that span"],
        [[1, 0, 0, 1, 0, 0], 1, "agents 1 and 4 — two readings, but antiparallel bisectors"],
        [[1, 0, 1, 0, 0, 0], 0, "agents 1 and 3 — two readings that span"],
        [[1, 0, 0, 0, 0, 0], 1, "a single scalar"],
        [[0, 0, 0, 0, 0, 0], 3, "nothing observed — two translations plus the gauge"],
        [[2, 2, 2, 2, 2, 2], 0, "everyone pinned"]
    ];
    for (const [ranks, expected, why] of cases) {
        assertEqual(nullity(HEX, ranks, HEX_EDGES), expected, `${ranks} (${why})`);
    }
});

test("wiring, with observers 1, 3, 5 at rank 1", () => {
    const ranks = OBSERVERS_135;
    const cycle = cycleEdges(6);
    const cases = [
        [cycle, 0, "full cycle"],
        [cycle.filter((e) => !(e[0] === 0 && e[1] === 1)), 0, "a path is still rigid"],
        [cycle.filter((e) => !(e[0] === 0 && e[1] === 1) && !(e[0] === 3 && e[1] === 4)), 1,
            "split in half — the halves drift apart"],
        [[], 12, "no consensus edges at all"]
    ];
    for (const [edges, expected, why] of cases) {
        assertEqual(nullity(HEX, ranks, edges), expected, why);
    }
    assertEqual(nullity(HEX, new Array(6).fill(2), []), 0,
        "no consensus edges, every agent at rank 2 — wiring is then redundant");
});

/* --- 4. the particular solution does not matter ------------------------ */

section("4. projection invariance");

/**
 * The whole "a min-norm SVD solve is interchangeable with Julia's LDLᵀ solve" argument rests
 * on this: harmonicReference lands on the point of the solution set nearest the agents'
 * current configuration, and for orthonormal N, (I − NNᵀ)N = 0. So perturbing the particular
 * solution along the null space must change nothing. If this fails, the port is not
 * comparable to the Julia at all.
 */
test("perturbing along the null space leaves the reference unchanged", () => {
    const ranks = [1, 0, 0, 1, 0, 0];                       // nullity 1
    const sheaf = X.buildSheaf(HEX, ranks, HEX_EDGES);
    const extension = X.harmonicExtension(sheaf, [0.4, 0.2, 1]);
    const N = extension.nullSpace;
    assert(N.cols > 0, "this fixture needs a non-trivial null space");

    const current = new Float64Array(6 * D);
    const random = rng(7);
    for (let i = 0; i < 6; i++) {
        current[D * i] = HEX[i][0] + 0.4 + 0.2 * (random() - 0.5);
        current[D * i + 1] = HEX[i][1] + 0.2 + 0.2 * (random() - 0.5);
        current[D * i + 2] = 1;
    }

    // pv + N Nᵀ(current − pv), for two particular solutions differing by a null vector.
    function project(pv) {
        const out = Float64Array.from(pv);
        const delta = new Float64Array(pv.length);
        for (let i = 0; i < pv.length; i++) delta[i] = current[i] - pv[i];
        const scratch = new Float64Array(N.cols);
        for (let j = 0; j < N.cols; j++) {
            let dot = 0;
            for (let i = 0; i < N.rows; i++) dot += N.data[i * N.cols + j] * delta[i];
            scratch[j] = dot;
        }
        for (let i = 0; i < N.rows; i++) {
            let sum = 0;
            for (let j = 0; j < N.cols; j++) sum += N.data[i * N.cols + j] * scratch[j];
            out[i] += sum;
        }
        return out;
    }

    const shifted = Float64Array.from(extension.x);
    for (let j = 0; j < N.cols; j++) {
        const coefficient = 3.7 * (j + 1);
        for (let i = 0; i < N.rows; i++) shifted[i] += coefficient * N.data[i * N.cols + j];
    }

    const a = project(extension.x);
    const b = project(shifted);
    for (let i = 0; i < a.length; i++) assertClose(a[i], b[i], 1e-10, `dof ${i}`);
});

/* --- 5. one observer, and where its free direction points -------------- */

section("5. solo-observer geometry");

/**
 * With agent 3 the only observer at rank 1, one direction is undetermined — and it must be
 * the one perpendicular to that agent's bisector, uniformly across the whole formation. This
 * ties the null space to the geometry rather than merely counting its dimension.
 */
test("the free direction is perpendicular to the lone bisector", () => {
    const ranks = ranksFrom([2]);                            // agent 3, one-based
    const sheaf = X.buildSheaf(HEX, ranks, HEX_EDGES);
    const N = X.harmonicExtension(sheaf, [0, 0, 1]).nullSpace;
    assertEqual(N.cols, 1, "nullity");

    const u = X.bisectorDirections(HEX)[2];
    const w = [N.data[0], N.data[1]];                        // agent 0's block
    const norm = Math.hypot(w[0], w[1]);
    assert(norm > 1e-6, "the free direction should move the agents");
    assertClose((w[0] * u[0] + w[1] * u[1]) / norm, 0, 1e-9, "component along the bisector");

    for (let i = 1; i < 6; i++) {
        assertClose(N.data[D * i], w[0], 1e-9, `agent ${i} x`);
        assertClose(N.data[D * i + 1], w[1], 1e-9, `agent ${i} y`);
        assertClose(N.data[D * i + 2], N.data[2], 1e-9, `agent ${i} gauge`);
    }
});

/* --- 6. translation bars ---------------------------------------------- */

section("6. translation bars");

function bars(ranks, edges = HEX_EDGES) {
    const sim = hexagonSim();
    sim.state.edges = edges.map((e) => e.slice());
    sim.setRanks(ranks);
    return sim.snapshot().null_directions;
}

test("a single rank-1 observer draws one bar, across the ring", () => {
    const drawn = bars(ranksFrom([2]));
    assertEqual(drawn.length, 1, "bar count");
    const u = X.bisectorDirections(HEX)[2];
    assertClose(drawn[0].dir[0] * u[0] + drawn[0].dir[1] * u[1], 0, 1e-7,
        "the bar should lie across the bisector, not along it");
});

test("no observers at all draws nothing", () => {
    // Every agent is free in the whole plane, so no agent has a distinguished direction —
    // drawing one would dress an arbitrary basis choice up as structure.
    assertEqual(bars(new Array(6).fill(0)).length, 0, "bar count");
});

test("a fully determined formation draws nothing", () => {
    assertEqual(bars(OBSERVERS_135).length, 0, "bar count");
});

test("antipodal rank-1 observers share one bar", () => {
    const drawn = bars([1, 0, 0, 1, 0, 0]);
    assertEqual(drawn.length, 1, "bar count");
});

/* --- 7. edges are normalised in both directions ------------------------ */

section("7. edge normalisation");

test("an edge wired one way can be cut the other way", () => {
    const sim = hexagonSim();
    const before = sim.state.edges.length;
    sim.disconnectAgents(5, 0);                 // the wrap-around edge, built as (5, 0)
    assertEqual(sim.state.edges.length, before - 1, "cutting (5,0)");

    sim.connectAgents(5, 0);
    assertEqual(sim.state.edges.length, before, "re-wiring");
    sim.disconnectAgents(0, 5);                 // ... and now from the other side
    assertEqual(sim.state.edges.length, before - 1, "cutting (0,5)");
});

test("wiring the same pair twice is a no-op", () => {
    const sim = createSimulation();
    sim.addNode([0.5, 0]);
    sim.addNode([0, 0.5]);
    sim.connectAgents(0, 1);
    sim.connectAgents(1, 0);
    assertEqual(sim.state.edges.length, 1, "edge count");
});

test("six agents admit fifteen edges and no more", () => {
    const sim = hexagonSim();
    for (let a = 0; a < 6; a++) for (let b = a + 1; b < 6; b++) sim.connectAgents(a, b);
    assertEqual(sim.state.edges.length, constants.MAX_EDGES, "complete graph on six vertices");
    assertEqual(sim.state.edges.length, 15, "C(6,2)");
    // Nothing left to add, but the cap must not corrupt anything either.
    sim.connectAgents(0, 3);
    assertEqual(sim.state.edges.length, 15, "still fifteen");
    assertEqual(nullity(HEX, OBSERVERS_135, sim.state.edges), 0, "fully wired and determined");
});

/* --- 7b. the board starts empty --------------------------------------- */

section("7b. an empty board");

test("a fresh simulation has a target and no agents", () => {
    const sim = createSimulation();
    const snapshot = sim.snapshot();
    assertEqual(snapshot.n_agents, 0, "agent count");
    assertEqual(snapshot.edges.length, 0, "edge count");
    assertEqual(snapshot.undetermined, 0, "nothing to determine yet");
    assertEqual(snapshot.energy, 0, "energy");
});

test("reset returns to an empty board", () => {
    const sim = hexagonSim();
    assertEqual(sim.snapshot().n_agents, 6, "built");
    sim.reset();
    assertEqual(sim.snapshot().n_agents, 0, "cleared");
    assertEqual(sim.state.edges.length, 0, "edges cleared");
});

test("agents can be placed up to the maximum and no further", () => {
    const sim = createSimulation();
    for (let i = 0; i < constants.MAX_AGENTS + 3; i++) sim.addNode([0.2 * i, 0.1 * i]);
    assertEqual(sim.state.positions.length, constants.MAX_AGENTS, "agent count");
});

test("a board drawn by hand behaves like the built-in ring", () => {
    // The whole point of starting empty: what you draw is a real formation, not a special
    // case. Six agents on a hexagon with observers 1, 3, 5 must reproduce the nullity the
    // README states for the built-in ring.
    const sim = hexagonSim();
    assertEqual(sim.state.nullSpace.cols, 0, "determined");
    for (let frame = 0; frame < 600; frame++) sim.step(1 / 60);
    assertEqual(sim.snapshot().energy, 0, "an exact global section costs no energy");
});

/* --- 7c. energy reporting --------------------------------------------- */

section("7c. Dirichlet energy reporting");

test("settled formations report exactly zero", () => {
    const sim = hexagonSim();
    for (let frame = 0; frame < 900; frame++) sim.step(1 / 60);
    assertEqual(sim.snapshot().energy, 0, "residual float noise must not surface");
});

test("a displaced formation reports four decimals", () => {
    const sim = hexagonSim();
    sim.state.positions[0][0] += 0.5;
    const energy = sim.snapshot().energy;
    assert(energy > 0, `expected a positive energy, got ${energy}`);
    assertClose(energy, Math.round(energy * 1e4) / 1e4, 0, "rounded to 1e-4");
    // 0.5 along x displaces one agent against two consensus edges and its own observation.
    assert(energy > 0.1, `expected an appreciable energy, got ${energy}`);
});

/* --- 8. it stays finite under sustained driving ------------------------ */

section("8. stability");

test("3600 fixed steps with a scripted command sequence", () => {
    const sim = hexagonSim();
    const H = 1 / 60;
    let worstEnergy = 0;

    for (let frame = 0; frame < 3600; frame++) {
        const phase = frame / 60;
        sim.setCommand([Math.cos(0.7 * phase), Math.sin(1.3 * phase)]);
        if (frame === 600) sim.cycleRank(1);
        if (frame === 900) sim.disconnectAgents(2, 3);
        if (frame === 1200) sim.setRanks([0, 0, 0, 0, 0, 0]);
        if (frame === 1500) sim.setRanks(OBSERVERS_135);
        if (frame === 1800) sim.adjustGain(2.0);
        if (frame === 2100) sim.cycleFeedforward();
        if (frame === 2400) sim.removeNode(0);
        if (frame === 2700) sim.addNode([0.9, 0.3]);
        if (frame === 3000) sim.connectAgents(2, 3);      // restore the edge cut at frame 900
        sim.step(H);

        for (const p of sim.state.positions) {
            assert(Number.isFinite(p[0]) && Number.isFinite(p[1]),
                `agent position went non-finite at frame ${frame}: ${p}`);
        }
        worstEnergy = Math.max(worstEnergy, sim.snapshot().energy);
    }

    assert(worstEnergy < 1e4, `energy grew without bound: ${worstEnergy}`);
    const { target } = sim.state;
    assert(Math.abs(target[0]) <= constants.ARENA_X / 2 && Math.abs(target[1]) <= constants.ARENA_Y / 2,
        `target escaped the arena: ${target}`);
});

test("the formation converges onto a reachable target", () => {
    const sim = hexagonSim();
    // Agents are dropped exactly on their own offsets, so displace them first or there is
    // nothing to converge from.
    sim.state.positions.forEach((p) => { p[0] += 0.8; p[1] -= 0.5; });
    for (let frame = 0; frame < 600; frame++) sim.step(1 / 60);   // no command: target at rest
    const snapshot = sim.snapshot();
    assert(snapshot.lag < 1e-3, `residual lag ${snapshot.lag}`);
    assert(snapshot.energy < 1e-6, `residual energy ${snapshot.energy}`);
});

/* --- 9. the degenerate topologies a mouse can reach -------------------- */

section("9. degenerate rebuilds");

/**
 * Julia wraps _rebuild! in a try/catch because ChordalLDLt of an all-zero Laplacian throws —
 * and the catch then restores the *previous* sheaf, so a cleared board with one new agent
 * silently computes against a stale six-agent topology. A dense SVD handles a zero matrix
 * exactly, so this path is simply correct here, and these tests pin that down.
 */
test("one agent, no edges, rank 0", () => {
    const sim = createSimulation();
    sim.clearNodes();
    sim.addNode([0.7, -0.2]);
    assertEqual(sim.state.nullSpace.cols, 3, "nullity — the whole stalk is free");

    sim.step(1 / 60);
    assertClose(sim.state.positions[0][0], 0.7, 1e-9, "x should not move");
    assertClose(sim.state.positions[0][1], -0.2, 1e-9, "y should not move");
    assertEqual(sim.snapshot().n_agents, 1, "agent count");
});

test("an empty board steps without complaint", () => {
    const sim = createSimulation();
    sim.clearNodes();
    sim.setCommand([1, 0]);
    for (let frame = 0; frame < 60; frame++) sim.step(1 / 60);
    assert(sim.state.target[0] > 0, "the target should still drive");
    assertEqual(sim.snapshot().n_agents, 0, "agent count");
    assertEqual(sim.snapshot().energy, 0, "energy");
});

test("every rank zeroed holds shape and stops tracking", () => {
    const sim = hexagonSim();
    for (let frame = 0; frame < 600; frame++) sim.step(1 / 60);   // settle onto the target
    const settled = sim.state.positions.map((p) => p.slice());

    sim.setRanks([0, 0, 0, 0, 0, 0]);
    sim.setCommand([1, 0]);
    for (let frame = 0; frame < 300; frame++) sim.step(1 / 60);

    assert(sim.state.target[0] > 0.5, "the target should have moved away");
    for (let i = 0; i < settled.length; i++) {
        assertClose(sim.state.positions[i][0], settled[i][0], 1e-3, `agent ${i} x stayed put`);
        assertClose(sim.state.positions[i][1], settled[i][1], 1e-3, `agent ${i} y stayed put`);
    }
});

test("removing agents down to nothing, then rebuilding", () => {
    const sim = hexagonSim();
    for (let i = 5; i >= 0; i--) {
        sim.removeNode(i);
        sim.step(1 / 60);
    }
    assertEqual(sim.state.positions.length, 0, "agent count");
    sim.addNode([0.3, 0.3]);
    sim.addNode([-0.3, 0.3]);
    sim.connectAgents(0, 1);
    sim.cycleRank(0);
    sim.cycleRank(0);                                          // rank 2
    for (let frame = 0; frame < 600; frame++) sim.step(1 / 60);
    assert(sim.snapshot().lag < 1e-3, `residual lag ${sim.snapshot().lag}`);
});

/* --- 10. the Julia golden values --------------------------------------- */

section("10. golden values from CellularSheaves.jl");

const GOLDEN = join(HERE, "hexagon_reference.json");

test("hexagon_reference.json", () => {
    if (!existsSync(GOLDEN)) {
        console.log("       (skipped — run docs/scripts/export_hexagon_golden.jl to generate it)");
        return;
    }
    const golden = JSON.parse(readFileSync(GOLDEN, "utf8"));
    const offsets = X.regularOffsets(golden.n_agents, golden.radius);
    const ranks = ranksFrom(golden.observers_zero_based, golden.n_agents);
    const sheaf = X.buildSheaf(offsets, ranks, cycleEdges(golden.n_agents));

    for (const testCase of golden.cases) {
        const { x, nullSpace } = X.harmonicExtension(sheaf, [testCase.target[0], testCase.target[1], 1]);
        assertEqual(nullSpace.cols, testCase.nullity, `nullity at ${testCase.target}`);
        for (let i = 0; i < golden.n_agents; i++) {
            assertClose(x[D * i], testCase.q[i][0], 1e-9, `agent ${i} x at ${testCase.target}`);
            assertClose(x[D * i + 1], testCase.q[i][1], 1e-9, `agent ${i} y at ${testCase.target}`);
        }
    }
});

test("...and the closed form the golden file reduces to", () => {
    // Nullity is 0 there, so the harmonic extension is unique and equals the escort
    // formation exactly. Asserting this directly keeps the check meaningful if the JSON is
    // ever missing, and makes plain how little the golden file on its own proves.
    const radius = 0.35;
    const offsets = X.regularOffsets(6, radius);
    const sheaf = X.buildSheaf(offsets, ranksFrom([0, 2, 4]), cycleEdges(6));

    for (const target of [[0, 0], [0.4, -0.25], [-0.9, 0.6], [0.25, 0.4]]) {
        const { x } = X.harmonicExtension(sheaf, [target[0], target[1], 1]);
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI) / 3;
            assertClose(x[D * i], target[0] + radius * Math.cos(angle), 1e-9, `agent ${i} x`);
            assertClose(x[D * i + 1], target[1] + radius * Math.sin(angle), 1e-9, `agent ${i} y`);
            assertClose(x[D * i + 2], 1, 1e-9, `agent ${i} gauge`);
        }
    }
});

/* --- 11. the linear algebra itself ------------------------------------- */

section("11. linear algebra");

test("svdTall reconstructs a random matrix", () => {
    const random = rng(99);
    for (const [m, n] of [[18, 18], [18, 12], [7, 3], [4, 4]]) {
        const A = X.mat(m, n);
        for (let i = 0; i < A.data.length; i++) A.data[i] = 2 * random() - 1;
        const { U, S, V } = X.svdTall(A);

        for (let i = 0; i < m; i++) {
            for (let j = 0; j < n; j++) {
                let sum = 0;
                for (let k = 0; k < n; k++) sum += U.data[i * n + k] * S[k] * V.data[j * n + k];
                assertClose(sum, A.data[i * n + j], 1e-10, `${m}x${n} entry (${i},${j})`);
            }
        }
        for (let k = 1; k < n; k++) assert(S[k] <= S[k - 1] + 1e-12, "singular values descend");
    }
});

test("svdTall finds an exact null space", () => {
    // A rank-2 matrix built as an outer-product sum, so its kernel is known exactly.
    const A = X.mat(6, 4);
    for (let i = 0; i < 6; i++) {
        A.data[i * 4 + 0] = i + 1;
        A.data[i * 4 + 1] = 2 * (i + 1);          // twice column 0
        A.data[i * 4 + 2] = Math.sin(i);
        A.data[i * 4 + 3] = 2 * Math.sin(i);      // twice column 2
    }
    const N = X.nullBasis(X.svdTall(A));
    assertEqual(N.cols, 2, "nullity");

    for (let c = 0; c < N.cols; c++) {
        for (let i = 0; i < 6; i++) {
            let sum = 0;
            for (let j = 0; j < 4; j++) sum += A.data[i * 4 + j] * N.data[j * N.cols + c];
            assertClose(sum, 0, 1e-10, `A·n${c} row ${i}`);
        }
    }
});

test("nullBasis returns orthonormal columns", () => {
    // The projection in harmonicReference assumes this; Julia needs an explicit QR because
    // its LDLᵀ basis is neither orthonormal nor canonically signed.
    const sheaf = X.buildSheaf(HEX, new Array(6).fill(0), []);
    const N = X.harmonicExtension(sheaf, [0, 0, 1]).nullSpace;
    assert(N.cols >= 2, "this fixture needs a non-trivial null space");

    for (let a = 0; a < N.cols; a++) {
        for (let b = 0; b < N.cols; b++) {
            let dot = 0;
            for (let i = 0; i < N.rows; i++) dot += N.data[i * N.cols + a] * N.data[i * N.cols + b];
            assertClose(dot, a === b ? 1 : 0, 1e-10, `⟨n${a}, n${b}⟩`);
        }
    }
});

test("the pseudoinverse solves a singular system in the least-squares sense", () => {
    const sheaf = X.buildSheaf(HEX, [1, 0, 0, 1, 0, 0], HEX_EDGES);   // nullity 1
    const blocks = X.assembleBlocks(sheaf);
    const { x } = X.harmonicExtension(sheaf, [0.4, 0.2, 1]);

    const rhs = new Float64Array(blocks.LII.rows);
    X.matvec(blocks.LIB, [0.4, 0.2, 1], rhs);
    for (let i = 0; i < rhs.length; i++) rhs[i] = -rhs[i];

    const residual = new Float64Array(blocks.LII.rows);
    X.matvec(blocks.LII, x, residual);
    for (let i = 0; i < residual.length; i++) {
        assertClose(residual[i], rhs[i], 1e-9, `residual dof ${i}`);
    }
});

test("the bisector fallbacks fire where they should", () => {
    const straight = X.bisectorDirections([[-1, 0], [0, 0], [1, 0]]);
    assertClose(Math.hypot(straight[1][0], straight[1][1]), 1, 1e-12, "a straight vertex is unit");

    const coincident = X.bisectorDirections([[0, 0], [0, 0], [1, 0], [0, 1]]);
    for (const u of coincident) {
        assertClose(Math.hypot(u[0], u[1]), 1, 1e-12, "coincident vertices still give unit vectors");
    }

    const pair = X.bisectorDirections([[-1, 0], [1, 0]]);      // n < 3 → inward
    assertClose(pair[0][0], 1, 1e-12, "the left agent points right");
    assertClose(pair[1][0], -1, 1e-12, "the right agent points left");

    // On a regular polygon the bisector and the inward radial direction coincide, and only
    // then — this is what makes the arbitrary-shape path worth having.
    const regular = X.bisectorDirections(HEX);
    for (let i = 0; i < 6; i++) {
        const norm = Math.hypot(HEX[i][0], HEX[i][1]);
        assertClose(regular[i][0], -HEX[i][0] / norm, 1e-12, `agent ${i} x`);
        assertClose(regular[i][1], -HEX[i][1] / norm, 1e-12, `agent ${i} y`);
    }
});

/* --- report ------------------------------------------------------------ */

console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) {
    console.log("\nfailures:");
    for (const { name, err } of failures) console.log(`  ${name}\n    ${err.stack.split("\n")[0]}`);
    process.exit(1);
}

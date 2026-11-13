"""A small JSON API for correcting CV entries without opening the admin.

It exists so that a script or an AI assistant can fix a typo in a venue or add a
note to a talk, and nothing more: it reads and updates existing rows of the
models listed in ``EDITABLE_MODELS``, and it cannot create or delete anything,
touch uploaded files, change relations, or read or set a grant's page password.

Authentication is a bearer token compared against the ``CV_API_TOKEN``
environment variable. With that variable unset the whole API answers 404, so it
is off until it is configured.

    GET   /api/cv/                         the models and their editable fields
    GET   /api/cv/lookup/<tag>/            which row a CV number such as T12 is
    GET   /api/cv/<model>/?q=<text>        rows, optionally filtered by text
    GET   /api/cv/<model>/<pk>/            one row
    PATCH /api/cv/<model>/<pk>/            {"field": "new value", ...}
    PATCH /api/cv/<model>/<pk>/?dry_run=1  validate and show the diff, save nothing

Every saved change is validated with ``full_clean()`` (on the fields it changes) and recorded in the admin
history of the row (as the user ``cv-api``), so it shows up under History next
to edits made by hand.
"""
import hmac
import json
import logging
import os

from django.apps import apps
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from academic.models import Profile
from academic.site_data import cv_number_map

logger = logging.getLogger(__name__)

# The models the API may touch, by the name used in the URL.
EDITABLE_MODELS = {
    'profile': 'Profile',
    'reference': 'Reference',
    'talk': 'Talk',
    'grant': 'Grant',
    'proposal': 'Proposal',
    'course': 'Course',
    'education': 'Education',
    'experience': 'Experience',
    'service': 'Service',
    'review': 'Review',
    'student': 'Student',
    'award': 'Award',
    'deliveredproduct': 'DeliveredProduct',
    'innovation': 'Innovation',
    'techreport': 'TechReport',
    'milestone': 'Milestone',
    'collaborator': 'Collaborator',
}

# Fields that are never read or written, whatever the model.
HIDDEN_FIELDS = {'password', 'created_at', 'updated_at'}

API_USERNAME = 'cv-api'
LIST_LIMIT = 200


def _json(data, status=200):
    return JsonResponse(data, status=status, encoder=DjangoJSONEncoder,
                        json_dumps_params={'indent': 2, 'ensure_ascii': False})


def _error(message, status):
    return _json({'error': message}, status=status)


def _authorized(request):
    """Whether the request carries the configured token.

    Raises Http404 when no token is configured, so an unconfigured site does not
    advertise that the API exists.
    """
    expected = os.environ.get('CV_API_TOKEN', '')
    if not expected:
        raise Http404()
    header = request.headers.get('Authorization', '')
    scheme, _, supplied = header.partition(' ')
    if scheme.lower() != 'bearer' or not supplied:
        return False
    return hmac.compare_digest(supplied.strip().encode(), expected.encode())


def token_required(view):
    def wrapped(request, *args, **kwargs):
        if not _authorized(request):
            return _error('Missing or wrong bearer token.', 401)
        return view(request, *args, **kwargs)
    wrapped.__name__ = view.__name__
    wrapped.__doc__ = view.__doc__
    return csrf_exempt(wrapped)


def _model(name):
    if name not in EDITABLE_MODELS:
        raise Http404('Unknown model %r.' % name)
    return apps.get_model('academic', EDITABLE_MODELS[name])


def editable_fields(model):
    """Plain fields the API may read and change: no keys, files or relations."""
    fields = []
    for field in model._meta.concrete_fields:
        if (field.primary_key or field.is_relation or not field.editable
                or field.name in HIDDEN_FIELDS
                or isinstance(field, models.FileField)):
            continue
        fields.append(field)
    return fields


def _row(obj):
    data = {'id': obj.pk, 'label': str(obj)}
    for field in editable_fields(type(obj)):
        data[field.name] = field.value_from_object(obj)
    return data


def _model_name(model):
    for name, class_name in EDITABLE_MODELS.items():
        if class_name == model.__name__:
            return name
    return None


@token_required
def index(request):
    """The models the API serves and the fields each one lets you change."""
    return _json({
        'models': {
            name: [field.name for field in editable_fields(_model(name))]
            for name in EDITABLE_MODELS
        },
    })


@token_required
def lookup(request, tag):
    """Map a CV number (T12, J3, G1, ...) to the row that carries it."""
    profile = Profile.objects.first()
    if not profile:
        raise Http404('No profile.')
    wanted = tag.strip().upper()
    for (model, pk), number in cv_number_map(profile).items():
        if number.upper() == wanted:
            name = _model_name(model)
            obj = model.objects.get(pk=pk)
            return _json({'cv_number': number, 'model': name, 'id': pk,
                          'url': '/api/cv/%s/%s/' % (name, pk), 'row': _row(obj)})
    return _error('No entry is numbered %s on the CV.' % tag, 404)


@token_required
def collection(request, model_name):
    """Rows of one model. ``?q=`` keeps rows whose text fields contain it."""
    if request.method != 'GET':
        return _error('Use GET here, and PATCH on a single row.', 405)
    model = _model(model_name)
    rows = model.objects.all()
    query = request.GET.get('q', '').strip()
    if query:
        condition = Q()
        for field in editable_fields(model):
            if isinstance(field, (models.CharField, models.TextField)):
                condition |= Q(**{'%s__icontains' % field.name: query})
        rows = rows.filter(condition)
    rows = list(rows[:LIST_LIMIT + 1])
    return _json({'model': model_name, 'truncated': len(rows) > LIST_LIMIT,
                  'rows': [_row(obj) for obj in rows[:LIST_LIMIT]]})


@token_required
def item(request, model_name, pk):
    """Read one row (GET) or change some of its fields (PATCH)."""
    model = _model(model_name)
    try:
        obj = model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise Http404('No %s with id %s.' % (model_name, pk))

    if request.method == 'GET':
        return _json(_row(obj))
    if request.method != 'PATCH':
        return _error('Use GET or PATCH.', 405)

    try:
        changes = json.loads(request.body or b'{}')
    except ValueError:
        return _error('The body must be a JSON object.', 400)
    if not isinstance(changes, dict) or not changes:
        return _error('The body must be a non-empty JSON object of field: value.', 400)

    fields = {field.name: field for field in editable_fields(model)}
    unknown = sorted(set(changes) - set(fields))
    if unknown:
        return _error('Not editable through the API: %s. Editable: %s.'
                      % (', '.join(unknown), ', '.join(sorted(fields))), 400)

    before = _row(obj)
    problems = {}
    for name, value in changes.items():
        try:
            setattr(obj, name, fields[name].to_python(value) if value is not None else None)
        except ValidationError as error:
            problems[name] = error.messages
    if problems:
        return _error(problems, 400)
    # Validate only what this request changes, so an old row that predates a
    # constraint on some other field can still be corrected.
    untouched = [f.name for f in model._meta.fields if f.name not in changes]
    try:
        obj.full_clean(exclude=untouched)
    except ValidationError as error:
        return _error(error.message_dict if hasattr(error, 'message_dict') else error.messages, 400)

    diff = {name: {'from': before[name], 'to': fields[name].value_from_object(obj)}
            for name in changes if before[name] != fields[name].value_from_object(obj)}
    dry_run = request.GET.get('dry_run') in ('1', 'true', 'yes')
    if diff and not dry_run:
        with transaction.atomic():
            obj.save()
            _record(obj, sorted(diff))
        logger.info('CV API changed %s %s: %s', model_name, pk, ', '.join(sorted(diff)))
    return _json({'model': model_name, 'id': obj.pk, 'saved': bool(diff) and not dry_run,
                  'dry_run': dry_run, 'changes': diff, 'row': _row(obj)})


def _record(obj, field_names):
    """Add the change to the row's admin history."""
    User = get_user_model()
    user, created = User.objects.get_or_create(username=API_USERNAME)
    if created:
        user.set_unusable_password()
        user.save()
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj)[:200],
        action_flag=CHANGE,
        change_message=json.dumps([{'changed': {'fields': field_names}}]),
    )

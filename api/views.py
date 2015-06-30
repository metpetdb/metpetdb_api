import ast
import json
from itertools import chain
from itsdangerous import URLSafeTimedSerializer

from getenv import env
from django.http import HttpResponse, HttpResponseNotFound
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.hashers import make_password
from tastypie.models import ApiKey

from .models import User, generate_confirmation_code, Image
from .api import MetpetAPI
from metpetdb import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context

def chem_analyses_given_sample_filters(request):
    """View function to retrieve a list of chemical analysis IDs of samples
    which match the given sample search filters. This endpoint will be used by
    the search page when the user is searching for chemical analyses by selecting
    sample filters.
    """
    standard_filters = {'format': 'json', 'limit': 0}

    email = request.META.get('email', None)
    api_key = request.META.get('api_key', None)
    api = MetpetAPI(email, api_key).api

    # Get samples which match the given filters
    sample_filters = dict(ast.literal_eval(json.dumps(request.GET)))
    sample_filters['fields'] = 'sample_id'

    samples = api.sample.get(params=dict(chain(sample_filters.items(),
                                               standard_filters.items())))

    sample_ids = []
    for sample in samples.data['objects']:
        sample_ids.append(sample['sample_id'])

    # Get subsamples of samples which match the given filters
    subsample_filters = {'sample__sample_id__in': ','.join(map(str, sample_ids)),
                         'fields': 'subsample_id'}
    subsamples = api.subsample.get(params=dict(chain(subsample_filters.items(),
                                                     standard_filters.items())))

    subsample_ids = []
    for subsample in subsamples.data['objects']:
        subsample_ids.append(subsample['subsample_id'])

    # Get chemical analyses with subsamples which the ones we retrieved earler
    subsample_chem_filters = {'subsample__subsample_id__in':
                                ','.join(map(str, subsample_ids)),
                               'fields': 'chemical_analysis_id'}
    subsample_chemical_analyses = api.chemical_analysis.get(
                                  params= dict(chain(subsample_chem_filters.items(),
                                                     standard_filters.items())))

    chemical_analysis_ids = []
    for analysis in subsample_chemical_analyses.data['objects']:
        chemical_analysis_ids.append(analysis['chemical_analysis_id'])

    results = {}
    results['chemical_analysis_ids'] = ','.join(map(str, chemical_analysis_ids))

    return HttpResponse(json.dumps(results), content_type='application/json')


@csrf_exempt
@transaction.atomic
def register(request):
    json_data = json.loads(request.body)

    try:
        User.objects.get(email=json_data['email'])
        data = {
            'result': 'failed',
            'message': 'email is already taken'
        }
        return HttpResponseForbidden(json.dumps(data),
                                     content_type='application/json')
    except:
        allowed_params = ["name", "email", "address", "city", "password",
                          "province", "country", "postal_code"]

        user = User()
        user.version = 1
        for param, value in json_data.iteritems():
            if param in allowed_params:
                setattr(user, param, value)

    user.enabled = 'N'
    user.contributor_enabled = 'N'
    user.confirmation_code = ''
    user.contributor_code = ''

    username = ''.join(c for c in user.email if c.isalnum() or
                                                    c in ['_', '@',
                                                        '+', '.',
                                                        '-'])[:30]
    password = make_password(json_data['password'])
    auth_user = AuthUser.objects.create(username=username,
                                        password=password,
                                        email=user.email,
                                        is_staff=False,
                                        is_active=True,
                                        is_superuser=False)

    user.django_user = auth_user
    user.save()
    ApiKey.objects.create(user=auth_user)

    data = {
        'result': 'success',
        'message': 'user registration successful',
        'email': user.email
    }
    return HttpResponse(json.dumps(data), content_type='application/json')


@csrf_exempt
def authenticate(request):
    try:
        user = User.objects.get(email=request.POST.get('email'))
    except:
        data = {
            'result': 'failed',
            'message': 'invalid email address'
        }
        return HttpResponseForbidden(json.dumps(data),
                                     content_type='application/json')
    if user.django_user.check_password(request.POST.get('password')):
        data = {
            'result': 'success',
            'email': user.email,
            'api_key': user.django_user.api_key.key
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        data = {
            'status': 'failed',
            'message': 'authentication failed'
        }
        return HttpResponseForbidden(json.dumps(data),
                                     content_type='application/json')


@csrf_exempt
def reset_password(request, token=None):
    serializer = URLSafeTimedSerializer(env('RESET_PWD_KEY'),
                                        salt=env('RESET_PWD_SALT'))
    if request.method == 'POST':
        try:
            if request.POST.get('token'):
                sig_okay, email = serializer.loads_unsafe(
                                      request.POST.get('token'))
                if not sig_okay:
                    data = {'result': 'failed',
                            'reason': 'reset token has expired'}
                    return HttpResponseBadRequest(
                        json.dumps(data),
                        content_type='application/json'
                    )
            else:
                email = request.POST.get('email', None)
            user = User.objects.get(email=email)
        except:
            return HttpResponseNotFound("Invalid email address")

        if user.enabled == 'Y':
            if request.POST.get('password'):
                try:
                    django_user = user.django_user
                    django_user.password = make_password(
                                               request.POST.get('password'))
                    django_user.save()
                    data = {'result': 'success',
                            'email': user.email,
                            'api_key': user.django_user.api_key.key}
                    return HttpResponse(json.dumps(data),
                                        content_type='application/json')
                except:
                    data = {'result': 'failed'}
                    return HttpResponseBadRequest(json.dumps(data),
                                              content_type='application/json')
            else:
                reset_token = serializer.dumps(user.email)
                data = {
                    'status': 'success',
                    'email': user.email,
                    'reset_token': reset_token
                }
                return HttpResponse(json.dumps(data),
                                    content_type='application/json')

    if request.method == 'GET':
        if token:
            serializer = URLSafeTimedSerializer(env('RESET_PWD_KEY'),
                                                salt=env('RESET_PWD_SALT'))
            sig_okay, email = serializer.loads_unsafe(token, max_age=86400)
            if sig_okay:
                data = {
                    'result': 'success',
                    'email': email
                }
                return HttpResponse(json.dumps(data),
                                    content_type='application/json')

        data = {'status': 'failed',
                'reason': 'invalid token'}
        return HttpResponseBadRequest(json.dumps(data),
                                      content_type='application/json')


@transaction.atomic
def confirm(request, conf_code):
    try:
        user = User.objects.get(confirmation_code=conf_code)
    except User.DoesNotExist:
        return HttpResponseNotFound("The confirmation code is invalid.")

    if user.enabled == 'Y':
        return HttpResponseForbidden("This account has already been confirmed")

    if user.auto_verify(conf_code):
        return HttpResponse("Thank you for confirming your email address!")
    else:
        return HttpResponse("Unable to confirm your email address.")

@transaction.atomic
def rawimage(request, cksum):
    try:
        path = settings.MEDIA_ROOT + cksum[0:2] + '/' + cksum[2:4] + '/' + cksum[4:]
        image_data = open(path, "rb").read()
        return HttpResponse(image_data, content_type="image/png")
    except: 
        return HttpResponseNotFound("Unable to open image file for reading")

@transaction.atomic
def request_contributor_access(request):
    try:
        user = User.objects.get(email=request.GET['email'])
    except:
        return HttpResponseNotFound("Invalid email address")

    if user.enabled == "N":
        return HttpResponseForbidden("Please confirm your email address first.")

    if user.contributor_code != '':
        return HttpResponseForbidden("You have already requested access.")

    if user.contributor_enabled == 'Y':
        return HttpResponseForbidden("This user is already a contributor")

    allowed_params = ['professional_url', 'research_interests',
                      'institution', 'reference_email']

    for param, value in request.GET.iteritems():
        if param in allowed_params:
            setattr(user, param, value)

    user.contributor_code = generate_confirmation_code(user.email)
    user.save()

    plaintext = get_template('request_contributor_access.txt')
    html      = get_template('request_contributor_access.html')

    d = Context({ 'name': env('SUPERUSER_NAME'),
                  'user': user,
                  'host_name': settings.HOST_NAME })

    subject = 'hello'
    from_email = env('DEFAULT_FROM_EMAIL')
    to = env('SUPERUSER_EMAIL')

    text_content = plaintext.render(d)
    html_content = html.render(d)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return HttpResponse("Your request to be added as a contributor has been submitted")


@transaction.atomic
def grant_contributor_access(request, contributor_code):
    try:
        user = User.objects.get(contributor_code=contributor_code)
    except User.DoesNotExist:
        return HttpResponseNotFound("The contributor code is invalid.")

    if user.contributor_enabled == 'Y':
        return HttpResponseForbidden("This user is already a contributor.")

    if user.manual_verify():
        return HttpResponse("This user is now a contributor!")
    else:
        return HttpResponseForbidden("Unable to make this user a contributor")

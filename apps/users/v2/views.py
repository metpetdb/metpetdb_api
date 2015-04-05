import ast
import json
import base64
import datetime
from itertools import chain
from django.views.decorators.http import require_GET, require_POST
from itsdangerous import URLSafeTimedSerializer

from getenv import env
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from jsonview.decorators import json_view
from jsonview.exceptions import BadRequest

from api.models import User, generate_confirmation_code
from metpetdb import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context

@csrf_exempt
@json_view
@require_POST
@transaction.atomic
def register(request):
    data = json.loads(request.body)
    
    user, created = User.objects.get_or_create(data)

    # if a new user isn't created, it means that either the user already exists
    # or there was an error processing the request; raise HTTP 400 either way
    if not created:
        raise BadRequest("Registration failed. Please try again.")
    else:
        return {
            'data': {
                'result': 'success',
                'email': user.email
            }
        }


@csrf_exempt
@require_POST
@json_view
def authenticate(request):
    failure_message = {
        'data': {
            'result': 'failed',
            'message': 'authentication failed'
        }
    }
    try:
        user = User.objects.get(email=request.POST.get('email'))
    except:
        return failure_message, 401
    if user.check_password(request.POST.get('password')):
        return {
            'data': {
                'result': 'success',
                'email': user.email,
                'api_key': user.django_user.api_key.key
            }
        }
    else:
        return failure_message, 401

def _get_password_reset_serializer():
    return URLSafeTimedSerializer(env('RESET_PWD_KEY'),
                                  salt=env('RESET_PWD_SALT'))


@csrf_exempt
@require_POST
@json_view
def request_password_reset(request):
    serializer = _get_password_reset_serializer()
    email = request.POST.get('email')
    if not email:
        raise BadRequest("No email provided.")
    user = User.objects.get(email=email)
    reset_token = serializer.dumps(user.email)
    return {
        'data': {
            'email': user.email,
            'reset_token': reset_token
        }
    }


@csrf_exempt
@require_GET
@json_view
def validate_request_password_token(request):
    serializer = _get_password_reset_serializer()
    token = request.GET.get('reset_token')
    if not token:
        raise BadRequest("No reset token provided.")
    sig_okay, email = serializer.loads_unsafe(token, max_age=86400)
    if sig_okay:
        return {
            'email': email
        }
    else:
        raise BadRequest("Operation failed.")


@csrf_exempt
@require_POST
@json_view
def reset_password(request):
    serializer = _get_password_reset_serializer()
    email = request.POST.get('email')
    token = request.POST.get('token')
    sig_okay, token_email = serializer.loads_unsafe(token, max_age=86400)
    if sig_okay and email == token_email:
        user = User.objects.get(email=email)
        user.password = make_password(request.POST.get('password'))
        user.django_user.password = user.password
        user.save()
        user.django_user.save()
    else:
        raise BadRequest("Operation failed.")


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

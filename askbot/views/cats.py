from categories.models import Category
from mptt.templatetags.mptt_tags import cache_tree_children

#from django.db import IntegrityError
from django.core import exceptions
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.translation import ugettext as _

from askbot.conf import settings as askbot_settings
from askbot.skins.loaders import render_into_skin


def cats(request):
    """
    View that renders a simple page showing the categories tree widget.
    It uses JSON to send tree data in the context to the client.
    """
    if askbot_settings.ENABLE_CATEGORIES:
        return render_into_skin(
            'categories.html',
            {'cats_tree':simplejson.dumps(generate_tree())},
            request
        )
    else:
        raise Http404

def generate_tree():
    """
    Traverses a node tree and builds a structure easily serializable as JSON.
    """
    roots = cache_tree_children(Category.tree.all())
    if roots:
        # Assume we have one tree for now, this could change if we decide
        # against storing the root node in the DB
        return _recurse_tree(roots[0])
    return {}

def _recurse_tree(node):
    """
    Helper recursive function for generate_tree().
    Traverses recursively the node tree.
    """
    output = {'name': node.name, 'id': (node.tree_id, node.lft)}
    children = []
    if not node.is_leaf_node():
        for child in node.get_children():
            children.append(_recurse_tree(child))
    output['children'] = children
    return output

def add_category(request):
    """
    Adds a category. Meant to be called by the site administrator using ajax
    and POST HTTP method.
    The expected json request is an object with the following keys:
      'name':   Name of the new category to be created.
      'parent': ID of the parent category for the category to be created.
    The response is also a json object with keys:
      'success': boolean
      'message': text description in case of failure (not always present)

    Node IDs are two-elements [tree_id, left id] JS arrays (Python tuples)
    """
    if not askbot_settings.ENABLE_CATEGORIES:
        raise Http404
    response_data = dict()
    try:
        if request.is_ajax():
            if request.method == 'POST':
                post_data = simplejson.loads(request.raw_post_data)
                if request.user.is_authenticated():
                    if request.user.is_administrator():
                        parent = None
                        if post_data.get('parent'):
                            try:
                                parent = Category.objects.get(
                                        tree_id=post_data['parent'][0],
                                        lft=post_data['parent'][1]
                                    )
                            except Category.DoesNotExist:
                                raise exceptions.ValidationError(
                                    _("Requested parent node doesn't exist")
                                    )
                        cat, created = Category.objects.get_or_create(name=post_data['name'], parent=parent)
                        if not created:
                            raise exceptions.ValidationError(
                                _('There is already a category with that name')
                                )
                        response_data['success'] = True
                        data = simplejson.dumps(response_data)
                        return HttpResponse(data, mimetype="application/json")
                    else:
                        raise exceptions.PermissionDenied(
                            _('Sorry, but you cannot access this view')
                        )
                else:
                    raise exceptions.PermissionDenied(
                        _('Sorry, but anonymous users cannot access this view')
                    )
            else:
                raise exceptions.PermissionDenied('must use POST request')
        else:
            #todo: show error page but no-one is likely to get here
            return HttpResponseRedirect(reverse('index'))
    except Exception, e:
        message = unicode(e)
        if message == '':
            message = _('Oops, apologies - there was some error')
        response_data['message'] = message
        response_data['success'] = False
        data = simplejson.dumps(response_data)
        return HttpResponse(data, mimetype="application/json")

def rename_category(request):
    """
    Change the name of a category. Meant to be called by the site administrator
    using ajax and POST HTTP method.
    The expected json request is an object with the following keys:
      'id':   ID of the parent category for the category to be created.
      'name': New name of the category.
    The response is also a json object with keys:
      'success': boolean
      'message': text description in case of failure (not always present)

    Node IDs are two-elements [tree_id, left id] JS arrays (Python tuples)
    """
    if not askbot_settings.ENABLE_CATEGORIES:
        raise Http404
    response_data = dict()
    try:
        if request.is_ajax():
            if request.method == 'POST':
                post_data = simplejson.loads(request.raw_post_data)
                if request.user.is_authenticated():
                    if request.user.is_administrator():
                        try:
                            node = Category.objects.get(
                                    tree_id=post_data['id'][0],
                                    lft=post_data['id'][1]
                                )
                        except Category.DoesNotExist:
                            raise exceptions.ValidationError(
                                _("Requested node doesn't exist")
                                )
                        new_name = post_data['name']
                        try:
                            node = Category.objects.get(
                                    name=new_name
                                )
                        except Category.DoesNotExist:
                            pass
                        else:
                            raise exceptions.ValidationError(
                                _('There is already a category with that name')
                                )
                        node.name=new_name
                        # Let any exception that happens during save bubble up,
                        # for now
                        node.save()
                        response_data['success'] = True
                        data = simplejson.dumps(response_data)
                        return HttpResponse(data, mimetype="application/json")
                    else:
                        raise exceptions.PermissionDenied(
                            _('Sorry, but you cannot access this view')
                        )
                else:
                    raise exceptions.PermissionDenied(
                        _('Sorry, but anonymous users cannot access this view')
                    )
            else:
                raise exceptions.PermissionDenied('must use POST request')
        else:
            #todo: show error page but no-one is likely to get here
            return HttpResponseRedirect(reverse('index'))
    except Exception, e:
        message = unicode(e)
        if message == '':
            message = _('Oops, apologies - there was some error')
        response_data['message'] = message
        response_data['success'] = False
        data = simplejson.dumps(response_data)
        return HttpResponse(data, mimetype="application/json")
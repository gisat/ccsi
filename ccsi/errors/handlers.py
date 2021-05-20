from flask import Blueprint, render_template, make_response, Response

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(400)
def error_400(error):
    template = render_template('errors/error.xml', msg=error)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response, 400

@errors.app_errorhandler(404)
def error_404(error):
    template = render_template('errors/error.xml', msg={'title': '(404) Page not found',
                                                        'summary': 'Page does not exist'})
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response, 404

@errors.app_errorhandler(501)
def error_501(error):
    template = render_template('errors/error.xml', title='(501) Not Implemented', error=error.description)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response, 501


class Errors:
    TYPE_ERRORS = {'ValidationError': '_marshmallow_exceptions',
                   'ValueError': '_value_error'}

    def __init__(self):
        pass

    def process_error(self, error):
        exception_class_name = error.__class__.__name__
        return self.__getattribute__(self.TYPE_ERRORS[exception_class_name]).__call__(error)
    def _marshmallow_exceptions(self, error):
        title = '(400) Bad Request'
        summary = 'Parameters validation error report: '
        for key, value in error.normalized_messages().items():
            if isinstance(value, list):
                summary += f'Parameter: {key}: {str.lower(*value)}, '
            else:
                summary += f'Parameter: {key}: {str.lower(value)}, '
        msg = {'title': title,
               'summary': summary}
        return msg, 400

    def _value_error(self, error):
        title = '(400) Bad Request'
        summary = 'Parameters validation error report: '
        for value in error.args:
                summary += value
        msg = {'title': title,
               'summary': summary}
        return msg, 400
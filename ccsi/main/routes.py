from flask import Blueprint, render_template
from pathlib import Path

main = Blueprint('main', __name__)


@main.route("/")
def index():
    """Show documentation"""

    # open readme
    with open(Path(main.root_path).parent.parent / 'README.md', 'r') as md:
        # read file
        content = md.read()
        # convert to HTML
        return render_template('main.html', title='Documentation', markdown=content)


# @main.route("/swag")
# def custom_swagger():
#     return render_template('ccsi_swagger.html')






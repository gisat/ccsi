from ccsi import create_app
from ccsi.config import Config

app = create_app()

if __name__ == '__main__':
    ####################
    # FOR DEVELOPMENT
    ####################
    app.run(host='0.0.0.0', port=8080, debug=Config.DEBUG)


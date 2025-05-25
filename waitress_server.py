from waitress import serve
from oikonomos import app



serve(app, host='0.0.0.0', port = 8000)
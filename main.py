from app.init import boot
import argparse
from flask import Flask, render_template, jsonify, request, abort, send_from_directory
from app.language import languages
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint
from flask_limiter import Limiter

parser = argparse.ArgumentParser(description='LibreTranslate - Free and Open Source Translation API')
parser.add_argument('--host', type=str,
                    help='Hostname (%(default)s)', default="127.0.0.1")
parser.add_argument('--port', type=int,
                    help='Port (%(default)s)', default=5000)
parser.add_argument('--char-limit', default=-1, metavar="<number of characters>",
                    help='Set character limit (%(default)s)')
parser.add_argument('--req-limit', default=-1, metavar="<number>",
                    help='Set maximum number of requests per hour per client (%(default)s)')
parser.add_argument('--google-analytics', default=None, metavar="<GA ID>",
                    help='Enable Google Analytics on the API client page by providing an ID (%(default)s)')

args = parser.parse_args()

boot()
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.errorhandler(400)
def invalid_api(e):
    return jsonify({"error": str(e.description)}), 400

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": str(e.description)}), 500

@app.route("/")
def index():
    return render_template('index.html', gaId=args.google_analytics)

@app.route("/languages")
def langs():
    """
    Retrieve list of supported languages
    ---
    tags:
      - translate
    responses:
      200:
        description: List of languages
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  code:
                    type: string
                    description: Language code
                  name:
                    type: string
                    description: Human-readable language name (in English)
                  charLimit:
                    type: string
                    description: Character input limit for this language (-1 indicates no limit)
    """
    return jsonify([{'code': l.code, 'name': l.name, 'charLimit': args.char_limit } for l in languages])

# Add cors
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin','*')
    response.headers.add('Access-Control-Allow-Headers', "Authorization, Content-Type")
    response.headers.add('Access-Control-Expose-Headers', "Authorization")
    response.headers.add('Access-Control-Allow-Methods', "GET, POST")
    response.headers.add('Access-Control-Allow-Credentials', "true")
    response.headers.add('Access-Control-Max-Age', 60 * 60 * 24 * 20)
    return response


@app.route("/translate", methods=['POST'])
def translate():
    """
    Translate text from a language to another
    ---
    tags:
      - translate
    parameters:
      - in: formData
        name: q
        schema:
          type: string
          example: Hello world!
        required: true
        description: Text to translate
      - in: formData
        name: source
        schema:
          type: string
          example: en
        required: true
        description: Source language code      
      - in: formData
        name: target
        schema:
          type: string
          example: es
        required: true
        description: Target language code
    responses:
      200:
        description: Translated text
        content:
          application/json:
            schema:
            type: object
            properties:
              translatedText:
                type: string
                description: Translated text
      400:
        description: Invalid request
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  description: Error message
      500:
        description: Translation error
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  description: Error message
    """

    if request.is_json:
        json = request.get_json()
        q = json.get('q')
        source_lang = json.get('source')
        target_lang = json.get('target')
    else:
        q = request.values.get("q")
        source_lang = request.values.get("source")
        target_lang = request.values.get("target")

    if not q:
        abort(400, description="Invalid request: missing q parameter")
    if not source_lang:
        abort(400, description="Invalid request: missing source parameter")
    if not target_lang:
        abort(400, description="Invalid request: missing target parameter")

    if args.char_limit != -1:
        q = q[:args.char_limit]

    src_lang = next(iter([l for l in languages if l.code == source_lang]), None)
    tgt_lang = next(iter([l for l in languages if l.code == target_lang]), None)

    if src_lang is None:
        abort(400, description="%s is not supported" % source_lang)
    if tgt_lang is None:
        abort(400, description="%s is not supported" % target_lang)

    translator = src_lang.get_translation(tgt_lang)
    try:
        return jsonify({"translatedText": translator.translate(q) })
    except Exception as e:
        abort(500, description="Cannot translate text: %s" % str(e))


swag = swagger(app)
swag['info']['version'] = "1.0"
swag['info']['title'] = "LibreTranslate"

@app.route("/spec")
def spec():
    return jsonify(swag)

SWAGGER_URL = '/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = 'http://petstore.swagger.io/v2/swagger.json'  # Our API url (can of course be a local resource)

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    "",
    config={  # Swagger UI config overrides
        'app_name': "LibreTranslate",
        "spec": swag
    }
)

app.register_blueprint(swaggerui_blueprint)

if __name__ == "__main__":
    app.run(host=args.host)
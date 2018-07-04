from typing import List
from apistar.server.core import generate_document
from apistar import Document, Include, Route
import json
from apistar.codecs import OpenAPICodec, JSONSchemaCodec
from flask import Flask, Blueprint
from flask import render_template, redirect, send_from_directory, send_file

# For Statics
import jinja2
import os
import apistar
import shutil

class Documentation():
    """Create documentation for Flask applications from endpoint function signatures"""

    codecs = {'openapi': OpenAPICodec,
              'jsonschema': JSONSchemaCodec}

    def __init__(self, app: Flask,
                 url: str = '',
                 title: str = '',
                 description: str = '',
                 version: str = '',
                 static_dir: str = 'static/',
                 docs_route: str = '/docs/'
                ):
        self.app: Flask = app
        self.url: str = url
        self.title: str = title
        self.description: str = description
        self.version: str = version
        self.static_dir: str = static_dir
        self.static_url: str = app.static_url_path
        self.docs_route: str = docs_route

        # TODO(OR): Complete blueprint stuff
        self.blueprints = app.iter_blueprints()
        self.seen_rules = set()
        self.includes: List[Include] = [self._blueprint_to_include(x) for x in self.blueprints]
        self.routes: List[Route] = self._extract_routes(app)
        self.doc: Document = self._build_doc()
        # Build static
        self._build_statics()
        self._register_docs_on_app()

    @staticmethod
    def _extract_blueprints(app):
        """Retrieve blueprints from Flask App"""
        return [x for x in app.iter_blueprints()]

    def _blueprint_to_include(self, blueprint: Blueprint):
        temp_app = Flask('temp_app')
        temp_app.register_blueprint(blueprint)
        routes = self._extract_routes(temp_app)
        url_prefix = blueprint.url_prefix
        return Include(url='', name=blueprint.name, routes=routes)

    def _extract_routes(self, app):
        """Convert Flask route map to APIStar Route List"""
        view_map = app.view_functions

        doc_routes = []
        for rule in app.url_map.iter_rules():
            handler = view_map[rule.endpoint]
            url = rule.rule
            # TODO(OR): Flask allows multiple methods, update to iterate new routes for each
            method = [method
                      for method in rule.methods
                      if method.upper() not in ['HEAD', 'OPTIONS']][0]
            
            rule_hash = (url, method)
            if rule_hash not in self.seen_rules:
                self.seen_rules.add(rule_hash)
                route = Route(url=url,
                              method=method,
                              handler=handler,
                              name=None,
                              documented=True,
                              standalone=False)

                # Exclude automatic Flask Routes
                if handler.__name__ not in ['send_static_file']:
                    doc_routes.append(route)
        return doc_routes

    def _build_doc(self):
        """Produce APIStar Document from APIStar Routes"""
        doc = generate_document(self.routes + self.includes)
        doc.url = self.url
        doc.title = self.title
        doc.description = self.description
        return doc

    def get_spec(self, codec='openapi'):
        """Render a documentation specification for requested codec"""
        return self.codecs[codec]().encode(self.doc)

    def _build_statics(self):
        document = self.doc
        loader = jinja2.PrefixLoader({
            'apistar': jinja2.PackageLoader('apistar', 'templates')
        })
        env = jinja2.Environment(autoescape=True, loader=loader)

        template = env.get_template('apistar/docs/index.html')
        code_style = None
        docs_directory = os.path.join(self.static_dir, 'docs')
        index_path = os.path.join(docs_directory, 'index.html')
        output_text = template.render(
            document=document,
            langs=['javascript', 'python'],
            code_style=code_style,
            static_url=lambda x: docs_directory + '/' + x
        )

        if not os.path.exists(docs_directory):
            os.makedirs(docs_directory)

        with open(index_path, 'w') as fout:
            fout.write(output_text)

        schema_path = os.path.join(docs_directory, 'openapi.json')
        with open(schema_path, 'wb') as fout:
            fout.write(self.get_spec())

        source_static_dir = os.path.join(os.path.dirname(apistar.__file__), 'static')
        doc_statics_dir = os.path.join(docs_directory, 'apistar')
        if os.path.exists(doc_statics_dir):
            shutil.rmtree(doc_statics_dir)
        shutil.copytree(source_static_dir, doc_statics_dir)

    def _register_docs_on_app(self):
        """Register the /docs/ endpoint on the Flask application"""

        @self.app.route(self.docs_route, methods=['GET'])
        def serve_api_documentation():
            """Serve index.html of api documentation"""
            docs_root = os.path.join(self.static_dir, 'docs')
            return send_from_directory(docs_root, 'index.html')
        

        @self.app.route(self.docs_route + 'openapi.json', methods=['GET'])
        def serve_schema():
            """Serve openapi json schema"""
            docs_root = os.path.join(self.static_dir, 'docs')
            return serve_static(docs_root + '/' + 'openapi.json')

        @self.app.route(self.docs_route + '<path:filename>', methods=['GET'])
        def serve_static(filename):
            """Serve static dependencies of api documentation"""
            # TODO(OR): Maket his OS safe
            path, filename = filename.rsplit('/', 1)
            return send_from_directory(path, filename)

        
    def __repr__(self):
        loaded = json.loads(self.get_spec())
        return json.dumps(loaded, indent=4)

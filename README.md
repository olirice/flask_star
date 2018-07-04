# flask_star
Porting apistar features to flask

### Project Scope:
 - API Documentation from flask endpiont function signatures (incomplete)
 - Dependency injection (not started)

#### API Documentation from function signatures
Functional
  - Native types
  - URL parameters
  - Query parameters
  - Endpoint groupings (groups by flask blueprint)

Not Functional
  - apistar typesystem objects
```python
from flask import Flask
from flask_star import Documentation

app = Flask(__name__)

@app.route('/welcome/{name}')
def welcome(name: str, title: str):
    return f'Welcome {title} {name}'

if __name__ == '__main__':
    api_docs = Documentation(app,
                             title='flask_star',
                             description='Basic flask_star example',
                             version='0.0.1',
                             static_dir='static/',
                             docs_route='/docs/')
    print(api_docs)
    app.run(debug=True, port=5000)
```

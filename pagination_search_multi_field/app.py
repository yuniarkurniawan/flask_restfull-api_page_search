from flask import Flask, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, sql, String, text
from flask_marshmallow import Marshmallow
from marshmallow import Schema, fields


BAD_REQUEST_400 = {
    "http_code": 400,
    "code": "badRequest",
    "message": "Bad request"
}

SUCCESS_200 = {
    'http_code': 200,
    'code': 'success'
}

SUCCESS_201 = {
    'http_code': 201,
    'code': 'success'
}

SUCCESS_204 = {
    'http_code': 204,
    'code': 'success'
}

INVALID_INPUT_422 = {
    "http_code": 422,
    "code": "invalidInput",
    "message": "Invalid input"
}


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_example.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)


class Author(db.Model):

    __tablename__ = "author"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30))
    created_date = db.Column(db.DateTime, server_default=db.func.now())
    books = db.relationship('Book', backref='Author',
                            cascade='all,delete-orphan')

    def __init__(self, **args) -> None:
        self.first_name = args['first_name']
        self.last_name = args['last_name']
        self.books = args['books']

    def __repr__(self):
        return f'<Author : {self.first_name}>'


class Book(db.Model):

    __tablename__ = "book"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer(), default=0)
    description = db.Column(db.String(255))
    created_date = db.Column(db.DateTime, server_default=db.func.now())
    author_id = db.Column(db.Integer(), db.ForeignKey('author.id'))
    author = db.relationship("Author",overlaps="Author,books")
    stock = db.Column(db.Integer(), default=0)

    def __init__(self, **args) -> None:
        self.title = args['title']
        self.description = args['description']
        self.year = args['year']
        self.stock = args['stock']


class BookSchema(ma.Schema):
    class Meta(ma.Schema.Meta):
        model = Book
        sqla_session = db.session

    id = fields.Integer(dump_only=True)
    title = fields.String(required=True)
    year = fields.String(required=True)
    description = fields.String()
    stock = fields.Integer()


class AuthorSchema(ma.Schema):
    class Meta(ma.Schema.Meta):
        model = Author
        sqla_session = db.session

    id = fields.Integer(dump_only=True)
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    created_date = fields.String(dump_only=True)
    total_books = fields.Integer()
    books = fields.Nested(BookSchema, many=True, only=['id','title', 'year', 'description'])



db.init_app(app)
with app.app_context():
    db.create_all()



@app.route("/api/v1/books/count_by_author", methods=['GET'])
def get_count_by_author():

    search = request.args.get('search', type=str)
    search = search.lower()

    sql_statement = """
        SELECT 
            author.first_name,
            count(book.id) as total_books
        FROM 
         book join author on book.author_id = author.id
        WHERE 
         lower(author.first_name) LIKE :search
         AND book.year = :year 
        GROUP BY author.id;
    """

    result = db.engine.execute(text(sql_statement), {"search": '%'+search+'%', "year": 2019}).fetchall()
    author_schema = AuthorSchema(many=True, only=['first_name', 'total_books'])
    list_out_data = author_schema.dump(result)

    return response_with(SUCCESS_200,
                             value={"data": list_out_data})


@app.route("/api/v1/books/book_by_author", methods=['GET'])
def get_book_data_by_author():

    try:

        list_out_data = []
        list_authors = Author.query.all()
        for data in list_authors:
            dict_author = {}
            dict_author['id'] = data.id
            dict_author['name'] = " ".join([data.first_name, data.last_name])

            book_schema = BookSchema(many=True)
            book_schema.dump(data.books)
            dict_author['total_books'] = len(data.books)
            dict_author['books'] = book_schema.dump(data.books)
            list_out_data.append(dict_author)

        return response_with(SUCCESS_200,
                             value={"data": list_out_data})

    except Exception as e:
        raise e



@app.route("/api/v1/books/update_stock/<int:book_id>", methods=['PATCH'])
def update_stock_book(book_id):
    data = request.get_json()
    db.session.begin()
    book = Book.query.get_or_404(book_id)
    if data.get('stock'): book.stock = book.stock + int(data['stock'])
    db.session.add(book)
    db.session.commit()
    book_schema = BookSchema()
    result = book_schema.dump(book)
    return response_with(SUCCESS_200, value={"book": result})


@app.route("/api/v1/authors", methods=['POST'])
def create_authors_books():

    try:
        data = request.get_json()
        author_schema = AuthorSchema()
        result = {}
        
        if data.get('books'):
            lists_books = list()
            for data_dict in data['books']:
                book = Book(title=data_dict['title'],
                            description=data_dict['description'],
                            year=data_dict['year'],
                            stock=0)
                lists_books.append(book)

            author = Author(first_name=data['first_name'],
                            last_name=data['last_name'],
                            books=lists_books)
            db.session.add(author)
            db.session.commit()
            result = author_schema.dump(author)
        else:
            author = Author(first_name=data['first_name'],
                            last_name=data['last_name'])
            db.session.add(author)
            db.session.commit()
            result = author_schema.dump(author)

        return response_with(SUCCESS_201, value={"author": result})

    except Exception as e:
        db.session.rollback()
        return response_with(INVALID_INPUT_422, value={"Expectation": str(e)})



@app.route("/api/v1/books", methods=['GET'])
def get_book_lists():

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    search = request.args.get('search', type=str)
    search = search.lower()

    try:

        fetch_book = db.session.query(Book.id,
                                      Book.title,
                                      Book.year,
                                      Book.description,
                                      Author.first_name,
                                      Author.last_name)\
            .join(Author, Book.author_id == Author.id)\
            .filter(func.lower(Book.title).like('%'+search+'%')
                    | func.lower(Book.description)
                    .like('%'+search+'%')
                    | func.cast(Book.year, String).like('%'+search+'%')
                    | func.lower(Author.first_name).like('%'+search+'%')
                    | func.lower(Author.last_name).like('%'+search+'%'))\
            .order_by(Book.id.desc())\
            .paginate(page=page, per_page=per_page)

        list_books = list()
        for data in fetch_book.items:
            dict_data = {}
            dict_data['id'] = data[0]
            dict_data['title'] = data[1]
            dict_data['year'] = data[2]
            dict_data['description'] = data[4]
            dict_data['author'] = data[4] + " " + data[5]
            list_books.append(dict_data)

        pagination = {
                "page": fetch_book.page,
                'pages': fetch_book.pages,
                'total_count': fetch_book.total,
                'prev_page': fetch_book.prev_num,
                'next_page': fetch_book.next_num,
                'has_next': fetch_book.has_next,
                'has_prev': fetch_book.has_prev,
            }

        return response_with(SUCCESS_200,
                             value={"data": list_books},
                             pagination=pagination)
    except Exception as e:
        return response_with(
                BAD_REQUEST_400,
                value={"Expectation": str(e)}
            )


def response_with(response, value=None, message=None, error=None,
                  headers={}, pagination=None):

    result = {}
    if value is not None:
        result.update(value)

    if response.get('message', None) is not None:
        result.update({'message': response['message']})

    result.update({'code': response['code']})

    if error is not None:
        result.update({'errors': error})

    if pagination is not None:
        result.update({'pagination': pagination})\

    headers.update({'Access-Control-Allow-Origin': '*'})
    headers.update({'server': 'FLask REST API'})

    return make_response(jsonify(result), response['http_code'], headers)




if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, sql, String
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


class Book(db.Model):

    __tablename__ = "book"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer(), default=0)
    description = db.Column(db.String(255))
    created_date = db.Column(db.DateTime, server_default=db.func.now())
    author_id = db.Column(db.Integer(), db.ForeignKey('author.id'))
    author = db.relationship("Author",)
    stock = db.Column(db.Integer(), default=0)

    def __init__(self, **args) -> None:
        self.title = args['title']
        self.description = args['description']
        self.year = args['year']


db.init_app(app)
with app.app_context():
    db.create_all()

'''
list_book_data = [
    {
        "title": "KKN Di Desa Penari",
        "description": "Novel fiksi misteri",
        "year": 2010
    },
    {
        "title": "Sewu Dino",
        "description": "Novel fiksi misteri",
        "year": 2019
    },
    {
        "title": "Jeritan Malam",
        "description": "Novel fiksi misteri",
        "year": 2020
    },
    {
        "title": "The Davinci Code",
        "description": "Novel fiksi ilmiah",
        "year": 2019
    },
    {
        "title": "Deception Point",
        "description": "Novel fiksi ilmiah",
        "year": 2009
    },
    {
        "title": "Digital Fortress",
        "description": "Novel fiksi ilmiah",
        "year": 2015
    },
    {
        "title": "The Lost Symbol",
        "description": "Novel fiksi ilmiah",
        "year": 2017
    },
    {
        "title": "Angles And Demonds",
        "description": "Novel fiksi ilmiah",
        "year": 2014
    },
    {
        "title": "The Origin",
        "description": "Novel fiksi ilmiah",
        "year": 2021
    }
]

list_author_book = list()
for data in list_book_data:
    book = Book(title=data['title'],
                description=data['description'],
                year=data['year'])
    list_author_book.append(book)

author = Author(first_name="Yuniar",
                last_name="Kurniawan",
                books=list_author_book)
db.session.add(author)
db.session.commit()
'''


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


# @app.route("/api/v1/books/maximum_stock", methods=['GET'])
# def get_book_maximum_Stock():

#     try:
#         fetch_book = Book.query.filter(func.max(Book.stock))
#     except Exception as e:
#         raise e


@app.route("/api/v1/books", methods=['GET'])
def get_book_lists():

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    search = request.args.get('search', type=str)
    search = search.lower()

    try:

        '''
        # fetch_book = Book.query.filter(func.lower(Book.title).like('%'+search+'%')
        #                            | func.lower(Book.description)
        #                            .like('%'+search+'%')
        #                            | sql.func.convert(sql.literal_column('VARCHAR(4)'), Book.year, sql.literal_column('4')).like('%'+search+'%'))\
        #     .order_by(Book.id.desc())\
        #     .paginate(page=page, per_page=per_page)


        # fetch_book = Book.query.filter(func.lower(Book.title).like('%'+search+'%')
        #                            | func.lower(Book.description)
        #                            .like('%'+search+'%')
        #                            | func.cast(Book.year, String).like('%'+search+'%'))\
        #     .order_by(Book.id.desc())\
        #     .paginate(page=page, per_page=per_page)

        # fetch_book = Book.query.join(Author) .filter(func.lower(Book.title).like('%'+search+'%')
        #                            | func.lower(Book.description)
        #                            .like('%'+search+'%')
        #                            | func.cast(Book.year, String).like('%'+search+'%'))\
        #     .order_by(Book.id.desc())\
        #     .paginate(page=page, per_page=per_page)
        '''

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
            # dict_data = {}
            # dict_data['id'] = data.id
            # dict_data['title'] = data.title
            # dict_data['year'] = data.year
            # dict_data['description'] = data.description
            # dict_data['author'] = data.author.first_name + " " + data.author.last_name
            # list_books.append(dict_data)
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


if __name__ == "__main__":
    app.run(debug=True)

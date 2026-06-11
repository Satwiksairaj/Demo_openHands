from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from extensions import db

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
    db.init_app(app)

    with app.app_context():
        from models import Book, Loan
        db.create_all()
        if not Book.query.first():  # Check if the database is empty
            sample_books = [
                Book(title='1984', author='George Orwell', isbn='0451524934', genre='Dystopian', total_copies=10, available_copies=10),
                Book(title='To Kill a Mockingbird', author='Harper Lee', isbn='0061120081', genre='Classic', total_copies=5, available_copies=5),
                Book(title='The Great Gatsby', author='F. Scott Fitzgerald', isbn='0743273567', genre='Classic', total_copies=3, available_copies=3),
                Book(title='Pride and Prejudice', author='Jane Austen', isbn='1503290565', genre='Romance', total_copies=7, available_copies=7),
                Book(title='The Catcher in the Rye', author='J.D. Salinger', isbn='0316769487', genre='Fiction', total_copies=4, available_copies=4),
            ]
            db.session.bulk_save_objects(sample_books)
            db.session.commit()

    @app.route('/books')
    def books():
        title_query = request.args.get('title', '')
        author_query = request.args.get('author', '')
        book_list = Book.query.filter(Book.title.contains(title_query),
                                      Book.author.contains(author_query)).all()
        return render_template('books.html', books=book_list)

    @app.route('/borrow', methods=['POST'])
    def borrow_book():
        isbn = request.form['isbn']
        borrower_name = request.form['borrower_name']
        book = Book.query.filter_by(isbn=isbn).first()
        if book and book.available_copies > 0:
            book.available_copies -= 1
            new_loan = Loan(book_id=book.id, borrower_name=borrower_name, borrowed_at=datetime.now())
            db.session.add(new_loan)
            db.session.commit()
            return 'Book borrowed successfully!'
        return 'Book not available', 400

    @app.route('/return', methods=['POST'])
    def return_book():
        isbn = request.form['isbn']
        book = Book.query.filter_by(isbn=isbn).first()
        if book:
            loan = Loan.query.filter_by(book_id=book.id, returned_at=None).first()
            if loan:
                loan.returned_at = datetime.now()
                book.available_copies += 1
                db.session.commit()
                return 'Book returned successfully!'
        return 'No active loan found', 400

    @app.route('/api/stats')
    def api_stats():
        total_books = Book.query.count()
        active_loans = Loan.query.filter(Loan.returned_at.is_(None)).count()
        overdue_loans = Loan.query.filter(Loan.returned_at.is_(None),
                                          Loan.borrowed_at < datetime.now() - timedelta(days=14)).count()
        top_books = db.session.query(Book.title, db.func.count(Loan.id).label('borrow_count'))\
                    .join(Loan, Loan.book_id == Book.id)\
                    .group_by(Book.id)\
                    .order_by(db.func.count(Loan.id).desc())\
                    .limit(5).all()
        return jsonify({
            'total_books': total_books,
            'active_loans': active_loans,
            'overdue_loans': overdue_loans,
            'top_books': [{'title': book[0], 'borrow_count': book[1]} for book in top_books]
        })

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)


@app.route('/books')
def books():
    title_query = request.args.get('title', '')
    author_query = request.args.get('author', '')
    book_list = Book.query.filter(Book.title.contains(title_query),
                                  Book.author.contains(author_query)).all()
    return render_template('books.html', books=book_list)

@app.route('/borrow', methods=['POST'])
def borrow_book():
    isbn = request.form['isbn']
    borrower_name = request.form['borrower_name']
    book = Book.query.filter_by(isbn=isbn).first()
    if book and book.available_copies > 0:
        book.available_copies -= 1
        new_loan = Loan(book_id=book.id, borrower_name=borrower_name, borrowed_at=datetime.now())
        db.session.add(new_loan)
        db.session.commit()
        return 'Book borrowed successfully!'
    return 'Book not available', 400

@app.route('/return', methods=['POST'])
def return_book():
    isbn = request.form['isbn']
    book = Book.query.filter_by(isbn=isbn).first()
    if book:
        loan = Loan.query.filter_by(book_id=book.id, returned_at=None).first()
        if loan:
            loan.returned_at = datetime.now()
            book.available_copies += 1
            db.session.commit()
            return 'Book returned successfully!'
    return 'No active loan found', 400

@app.route('/api/stats')
def api_stats():
    total_books = Book.query.count()
    active_loans = Loan.query.filter(Loan.returned_at.is_(None)).count()
    overdue_loans = Loan.query.filter(Loan.returned_at.is_(None),
                                      Loan.borrowed_at < datetime.now() - timedelta(days=14)).count()
    top_books = db.session.query(Book.title, db.func.count(Loan.id).label('borrow_count'))
                .join(Loan, Loan.book_id == Book.id)
                .group_by(Book.id)
                .order_by(db.func.count(Loan.id).desc())
                .limit(5).all()
    return jsonify({
        'total_books': total_books,
        'active_loans': active_loans,
        'overdue_loans': overdue_loans,
        'top_books': [{'title': book[0], 'borrow_count': book[1]} for book in top_books]
    })

if __name__ == '__main__':
    app.run(debug=True)

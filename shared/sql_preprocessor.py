from sklearn.base import BaseEstimator, TransformerMixin
from shared.progress import ProgressEstimator
import io, tokenize
import numpy as np
import re

class SQLPreprocessor(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        return np.array([self.remove_comments_and_to_lower(x) for x in X])

    @staticmethod
    def __remove_comments(source: str) -> str:
        lines = source.split("\n")
        out = ""
        for line in lines:
            if line.strip().startswith("--"):
                continue
            out += line + "\n"
        return out

    __mysql_keywords = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "ORDER BY",
        "GROUP BY", "HAVING", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN",
        "OUTER JOIN", "JOIN", "ON", "AS", "DISTINCT", "INSERT INTO",
        "VALUES", "UPDATE", "SET", "DELETE", "CREATE TABLE", "ALTER TABLE",
        "DROP TABLE", "PRIMARY KEY", "FOREIGN KEY", "REFERENCES", "INDEX",
        "UNIQUE", "AUTO_INCREMENT", "DESC", "ASC", "LIMIT", "OFFSET",
        "LIKE", "IN", "BETWEEN", "IS NULL", "IS NOT NULL",
        "INT", "VARCHAR", "CHAR", "TEXT", "FLOAT", "DOUBLE", "DECIMAL",
        "DATE", "TIME", "TIMESTAMP", "BOOLEAN", "BIT", "BLOB", "ENUM"
    ]

    __pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, __mysql_keywords)) + r')\b', re.IGNORECASE)

    # Function to capitalize matched keywords
    @staticmethod
    def __capitalize_match(match):
        return match.group(0).upper()

    @staticmethod
    def capitalize_keywords(source: str) -> str:
        return SQLPreprocessor.__pattern.sub(SQLPreprocessor.__capitalize_match, source)

    @staticmethod
    def remove_comments_and_to_lower(source: str) -> str:
        capitalized = SQLPreprocessor.capitalize_keywords(source)
        # print(source)
        # print('--------------')
        # print(capitalized)
        decommented = SQLPreprocessor.__remove_comments(capitalized)
        return decommented

__tests = [
"""
create table MovieTheatre(
	tid int primary key,
	Name varchar,
	Location varchar,
    --- this is a comment
	PostalCode varchar check (length(postalcode) = 6)
);

create type loyalty_tier as enum('none', 'bronze', 'silver', 'gold');

create table Customer(
	cid int primary key,
	name varchar,
	loyaltystatus loyalty_tier,
	hometheatre int,
    -- another comment
	constraint hometheatre_fk foreign key (hometheatre) references movietheatre(tid)
);

create table Watch(
	mid int,
	tid int,
	cid int,
	constraint moviewatch_fk foreign key (mid) references movie(mid),
	constraint theatrewatch_fk foreign key (tid) references movietheatre(tid),
	constraint customerwatch_fk foreign key (cid) references customer(cid),
	primary key(mid, tid, cid)
);

"""
]

def test_preprocessor():
    for test in __tests:
        # print(test)
        print(SQLPreprocessor.remove_comments_and_to_lower(test))
        print(len(test))
        print(len(SQLPreprocessor.capitalize_keywords(test)))
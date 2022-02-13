# Dinamopy

Dinamopy is a python helper library for [dynamodb](https://aws.amazon.com/dynamodb/). You can define your [access patterns](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-modeling-nosql-B.html) in a json file and can use dynamic method names to make operations.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install dinamopy.

```bash
pip install dinamopy
```

## Usage

### app.py
```python
from decimal import Decimal
import dinamopy


class MyHooks(dinamopy.DinamoHooks):
    def after_get(self, response):
        for k, v in response.items():
            if isinstance(v, Decimal):
                response[k] = int(v)
        return response

db = dinamopy.DinamoPy('dinamopy.json', MyHooks())

db.put(item={
    'customerId': 'xyz',
    'sk': 'CUST#xyz',
    'email': 'rasimandiran@outlook.com',
    'fullName': 'Rasim Andiran',
    'userPreferences': {'language': 'en', 'sort': 'date', 'sortDirection': 'ascending'}
})

db.overwrite(item={
    'customerId': 'xyz',
    'sk': 'CUST#xyz',
    'email': 'rasimandiran@outlook.com',
    'fullName': 'Rasim Andiran',
    'userPreferences': {'language': 'en', 'sort': 'date', 'sortDirection': 'ascending'}
})

db.get_customer_profile_by_customer_id(customerId='xyz')
db.get_bookmarks_by_customer_id(customerId='123')
db.get_customer_profile_by_email(email='shirley@example.net')
db.get_bookmarks_by_url(url='https://aws.amazon.com', customerId='123')
db.get_customer_folder(customerId='123', folder='Cloud')

db.update_customer_profile_by_customer_id(customerId='321', sk='CUST#321', new_fields={'email': 'rasimandiran@gmail.com'})
db.update_bookmarks_by_customer_id(customerId='123', sk='https://aws.amazon.com', new_fields={'folder': 'Tools'})
db.update_customer_profile_by_email(email='rasimandiran@gmail.com', new_fields={'fullName': 'Rasim Andiran'})
db.update_bookmarks_by_url(url='https://aws.amazon.com', customerId='123', new_fields={'description': 'Deneme'})
db.update_customer_folder(customerId='123', folder='Cloud', new_fields={'folder': 'CloudFolder'})

db.delete_customer_profile_by_customer_id(customerId='123')
db.delete_bookmarks_by_customer_id(customerId='123', sk='https://aws.amazon.com', new_fields={'folder': 'Tools'})
db.delete_customer_profile_by_email(email='rasimandiran@gmail.com', new_fields={'fullName': 'Rasim Andiran'})
db.delete_bookmarks_by_url(url='https://aws.amazon.com', customerId='123', new_fields={'description': 'Deneme'})
db.delete_customer_folder(customerId='123', folder='Cloud', new_fields={'folder': 'CloudFolder'})
```

### dinamopy.json
```json
{
    "region": "localhost",
    "port": 8000,
    "tableName": "CustomerBookmark",
    "partitionKey": "customerId", 
    "sortKey": "sk",
    "timestamps": true,
    "paranoid": true,
    "returnRawResponse": false,
    "logLevel": "debug",
    "accessPatterns": {
        "customerProfileByCustomerId": {
            "table": "table",
            "partitionKey": "customerId",
            "sortKey": "sk",
            "sortKeyOperator": "begins_with",
            "sortKeyValue": "CUST#"
        },
        "bookmarksByCustomerId": {
            "table": "table",
            "partitionKey": "customerId",
            "sortKey": "sk",
            "sortKeyOperator": "begins_with",
            "sortKeyValue": "http"
        },
        "customerProfileByEmail": {
            "table": "ByEmail",
            "partitionKey": "email"
        },
        "bookmarksByUrl": {
            "table": "ByUrl",
            "partitionKey": "url",
            "sortKey": "customerId"
        },
        "customerFolder": {
            "table": "ByCustomerFolder",
            "partitionKey": "customerId",
            "sortKey": "folder"
        }
    }
}
```


## To-Do
- More generic hooks
- Logging
- Tests
- Documentation

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
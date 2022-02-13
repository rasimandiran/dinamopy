import json
import logging
import logging.config
import time
import boto3 
from boto3.dynamodb.conditions import Key
from .dinamo_hooks import DinamoHooks


class DinamoPy:
    def __init__(self, config_file, hooks_class=None):
            config_file = open(config_file)
            config = json.load(config_file)
            config_file.close()
            self.__access_patterns = {k.lower(): v for k, v in config['accessPatterns'].items()}
            del config['accessPatterns']
            self.__config = config
            if self.__config['region'] == 'localhost':
                port = self.__config.get('port', 8000)
                dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:{}'.format(port), region_name='')
            else:
                dynamodb = boto3.resource('dynamodb', region_name=self.__config['region'])
            self.table = dynamodb.Table(self.__config['tableName'])
            if hooks_class:
                if isinstance(hooks_class, DinamoHooks):
                    self.__hooks = hooks_class
                else:
                    raise TypeError('Hooks class must be an instance of DinamoHooks')
            else:
                self.__hooks = DinamoHooks()
            self.__last_response_metadata = None

            log_level = self.__config.get('logLevel')
            if log_level:
                logging.config.dictConfig({
                    'version': 1,
                    'disable_existing_loggers': True,
                    'formatters': { 
                        'standard': { 
                            'format': '[%(levelname)s]: %(message)s'
                        },
                    },
                    'handlers': { 
                        'default': { 
                            'level': log_level.upper(),
                            'formatter': 'standard',
                            'class': 'logging.StreamHandler',
                            'stream': 'ext://sys.stdout',
                        },
                    },
                    'loggers': { 
                        '': {
                            'handlers': ['default'],
                            'level': log_level.upper(),
                            'propagate': False
                        }
                    }
                })

    def set_hooks(self, hooks_class):
        if isinstance(hooks_class, DinamoHooks):
            self.__hooks = hooks_class
        else:
            raise TypeError('Hooks class must be an instance of DinamoHooks')

    def get_last_metadata(self):
        return self.__last_response_metadata

    def get_all_config(self):
        return self.__config

    def get_config(self, key):
        return self.__config.get(key)

    def get_access_patterns(self):
        return self.__access_patterns

    def get_access_pattern(self, access_pattern):
        return self.__access_patterns.get(access_pattern)

    def __getattr__(self, method_name):
        def handlerFunction(**kwargs):
            method_parts = method_name.split("_")
            operation = method_parts[0]
            del method_parts[0]
            pattern_name = "".join(method_parts).lower()
            pattern = self.__access_patterns.get(pattern_name)
            if operation not in ('get', 'put', 'overwrite', 'delete', 'update'):
                raise ValueError('Operation "{}" not supported'.format(operation))
            if not pattern and operation not in ('put', 'overwrite'):
                raise AttributeError('Access pattern "{}" not found'.format(pattern_name))
            
            hook_kwargs = getattr(self.__hooks, 'before_'+operation)(**kwargs)
            if operation == 'put' and not method_parts:
                response = self.__put(hook_kwargs['item'])
            elif operation == 'overwrite' and not method_parts:
                response = self.__overwrite(hook_kwargs['item'])
            elif operation == 'get':
                response = self.__get(pattern, hook_kwargs[pattern['partitionKey']], hook_kwargs.get(pattern.get('sortKey')))
            elif operation == 'update':
                response = self.__update(pattern, hook_kwargs[pattern['partitionKey']], hook_kwargs.get(pattern.get('sortKey')), hook_kwargs['new_fields'])
            elif operation == 'delete':
                response = self.__delete(pattern, hook_kwargs[pattern['partitionKey']], hook_kwargs.get(pattern.get('sortKey')))
            return getattr(self.__hooks, 'after_'+operation)(response)
        return handlerFunction

    def __put(self, item):
        parameters = {}
        parameters['Key'] = {self.__config['partitionKey']: item[self.__config['partitionKey']]}
        if self.__config.get('sortKey'):
            parameters['Key'][self.__config['sortKey']] = item[self.__config['sortKey']]
        response = self.table.get_item(**parameters)

        if response.get('Item'):
            if response['Item'].get('deleted_at'):
                raise ValueError('Item already exists, but is marked as deleted. You must use overwrite instead of put or hard delete the item first.')
            else:
                raise ValueError('Item already exists. You must use overwrite instead of put.')
        
        if self.__config.get('timestamps'):
            item['created_at'] = int(time.time())
        response = self.table.put_item(Item=item, ReturnValues='ALL_OLD')
        self.__last_response_metadata = response['ResponseMetadata']
        if not self.__config.get('returnRawResponse'):
            return item
        else:
            return response

    def __overwrite(self, item):
        parameters = {}
        parameters['Key'] = {self.__config['partitionKey']: item[self.__config['partitionKey']]}
        if self.__config.get('sortKey'):
            parameters['Key'][self.__config['sortKey']] = item[self.__config['sortKey']]
        response = self.table.get_item(**parameters)

        if not response.get('Item'):
            raise ValueError('Item does not exist. You must use put instead of overwrite.')

        if response.get('Item') and self.__config.get('timestamps'):
            item['created_at'] = response['Item']['created_at']
            item['overwrote_at'] = int(time.time())

        response = self.table.put_item(Item=item, ReturnValues='ALL_OLD')
        self.__last_response_metadata = response['ResponseMetadata']
        if not self.__config.get('returnRawResponse'):
            return response.get('Attributes')
        else:
            return response

    def __get(self, pattern, pk, sk):
        parameters = {}
        sk_val = sk if sk else pattern.get('sortKeyValue')
        sk_operator = pattern.get('sortKeyOperator', 'eq') if not sk else 'eq'
        
        action = 'get_item'
        if pattern['table'] == 'table' and sk_operator == 'eq':
            parameters['Key'] = {pattern['partitionKey']: pk}
            if pattern.get('sortKey'):
                parameters['Key'][pattern['sortKey']] = sk_val
        
        else:
            action = 'query'
            parameters['KeyConditionExpression'] = Key(pattern['partitionKey']).eq(pk)
            if sk_val:
                parameters['KeyConditionExpression'] = parameters['KeyConditionExpression'] & getattr(Key(pattern['sortKey']), sk_operator)(sk_val)
            if pattern['table'] != 'table':
                parameters['IndexName'] = pattern['table']
        
        response = getattr(self.table, action)(**parameters)
        if action == 'get_item' and self.__config.get('paranoid') and response.get('Item', {}).get('deleted_at'):
            del response['Item']

        if action == 'query' and response.get('Items'):
            response['Items'] = [item for item in response['Items'] if not item.get('deleted_at')]

        self.__last_response_metadata = response['ResponseMetadata']
        if not self.__config.get('returnRawResponse'):
            if action == 'get_item':
                return response.get('Item')
            else:
                return response.get('Items')
        else:
            return response

    def __update(self, pattern, pk, sk, update_data):
        sk_val = sk if sk else pattern.get('sortKeyValue')
        sk_operator = pattern.get('sortKeyOperator', 'eq') if not sk else 'eq'
        
        if pattern['table'] != 'table':
            if not pattern.get('sortKey'):
                response = self.table.query(KeyConditionExpression=Key(pattern['partitionKey']).eq(pk), IndexName=pattern['table'])
            else:
                response = self.table.query(KeyConditionExpression=Key(pattern['partitionKey']).eq(pk) & getattr(Key(pattern['sortKey']), sk_operator)(sk_val), IndexName=pattern['table'])

            items = response['Items']
            if not items:
                raise ValueError('Item does not exist.')
            elif len(items) > 1:
                raise ValueError('More than one item found. You must use get instead of update.')
            elif items[0].get('deleted_at'):
                raise ValueError('Item is marked as deleted. You must use hard delete instead of update.')

            item = items[0]
            pk = item[self.__config['partitionKey']]
            sk_val = item.get(self.__config.get('sortKey'))

        parameters = {}
        if self.__config.get('timestamps'):
            update_data['updated_at'] = int(time.time())
        
        parameters['UpdateExpression'] = 'SET ' + ', '.join(['#{} = :{}'.format(k, k) for k in update_data.keys()])
        parameters['ExpressionAttributeNames'] = {'#{}'.format(k): k for k in update_data.keys()}
        parameters['ExpressionAttributeValues'] = {':{}'.format(k): v for k, v in update_data.items()}

        parameters['Key'] = {self.__config['partitionKey']: pk}
        if sk_val is not None:
            parameters['Key'][self.__config['sortKey']] = sk_val

        parameters['ReturnValues'] = 'ALL_NEW'
        response = self.table.update_item(**parameters)
        self.__last_response_metadata = response['ResponseMetadata']
        if not self.__config.get('returnRawResponse'):
            return response.get('Attributes')
        else:
            return response

    def __delete(self, pattern, pk, sk):
        sk_val = sk if sk else pattern.get('sortKeyValue')
        sk_operator = pattern.get('sortKeyOperator', 'eq') if not sk else 'eq'
        
        if pattern['table'] != 'table':
            if not pattern.get('sortKey'):
                response = self.table.query(KeyConditionExpression=Key(pattern['partitionKey']).eq(pk), IndexName=pattern['table'])
            else:
                response = self.table.query(KeyConditionExpression=Key(pattern['partitionKey']).eq(pk) & getattr(Key(pattern['sortKey']), sk_operator)(sk_val), IndexName=pattern['table'])

            items = response['Items']
            if not items:
                raise ValueError('Item does not exist.')
            elif len(items) > 1:
                raise ValueError('More than one item found. You must use get instead of delete.')
            elif items[0].get('deleted_at'):
                raise ValueError('Item is marked as deleted. You must use hard delete instead of delete.')

            item = response['Items'][0]
            pk = item[self.__config['partitionKey']]
            sk_val = item.get(self.__config.get('sortKey'))

        parameters = {}
        action = 'delete_item'
        parameters['Key'] = {self.__config['partitionKey']: pk}
        if sk_val is not None:
            parameters['Key'][self.__config['sortKey']] = sk_val
            parameters['ReturnValues'] = 'ALL_OLD'

        if self.__config.get('paranoid'):
            action = 'update_item'
            update_data = {'deleted_at': int(time.time())}
            parameters['UpdateExpression'] = 'SET ' + ', '.join(['#{} = :{}'.format(k, k) for k in update_data.keys()])
            parameters['ExpressionAttributeNames'] = {'#{}'.format(k): k for k in update_data.keys()}
            parameters['ExpressionAttributeValues'] = {':{}'.format(k): v for k, v in update_data.items()}
            parameters['ReturnValues'] = 'ALL_NEW'

        response = getattr(self.table, action)(**parameters)
        self.__last_response_metadata = response['ResponseMetadata']
        if not self.__config.get('returnRawResponse'):
            return response.get('Attributes')
        else:
            return response

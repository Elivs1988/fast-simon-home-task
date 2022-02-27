from flask import Flask, request

from google.cloud import datastore

app = Flask(__name__)

ds = datastore.Client()

variables_kind = 'variables'

def get_current(var_name):
    filters = [('name', '=', var_name), ('status', '=', 'current')]
    query = ds.query(kind=variables_kind, filters=filters)
    query_iter = query.fetch(limit=1)
    entity = None
    for res_entity in query_iter:
        entity = res_entity
    return entity

def get_lastly_changed():
    filters = [('lastly_changed', '=', True)]
    query = ds.query(kind=variables_kind, filters=filters)
    query_iter = query.fetch(limit=1)
    entity = None
    for res_entity in query_iter:
        return res_entity
    return entity

def create_stab(var_name, head):
    entity_key = ds.key(variables_kind)
    entity = ds.entity(key=entity_key)
    parent_id = None
    entity.update({
        'name': var_name,
        'value': None,
        'parent_id': None,
        'child_id': head.id,
        'status': 'current',
        'lastly_changed': True,
    })
    return entity

def set_variable(var_name, var_value):
    entity_key = ds.key(variables_kind)
    entity = ds.entity(key=entity_key)
    parent = get_current(var_name)
    parent_id = None
    entities = [entity]

    if parent:
        parent_id = parent.id
        parent['status'] = None
        entities.append(parent)

    entity.update({
        'name': var_name,
        'value': var_value,
        'parent_id': parent_id,
        'child_id': None,
        'status': 'current',
        'lastly_changed': True,
    })
    lastly_changed_entity = get_lastly_changed()
    if lastly_changed_entity:
        lastly_changed_entity['lastly_changed'] = False
        entities.append(lastly_changed_entity)
    ds.put_multi(entities)

def get_variable(var_name):
    current = get_current(var_name)
    if current:
        return current['value']

def unset_variable(var_name):
    current = get_current(var_name)
    if current:
        set_variable(var_name, None)
    
def num_equal_to(var_value):
    filters = [('value', '=', var_value), ('status', '=', 'current')]
    query = ds.query(kind=variables_kind, filters=filters)
    query_iter = query.fetch()
    res = 0
    for entity in query_iter:
        res += 1
    return res

def undo():
    last_changed_entity = get_lastly_changed()
    if not last_changed_entity:
        return 'NO COMMANDS'
    var_name = last_changed_entity['name']
    current = get_current(var_name)
    if not current or (not current['parent_id'] and not current['value']):
        return 'NO COMMANDS'
    current['lastly_changed'] = False
    if not current['parent_id'] and current['value']:
        current['status'] = None
        current['lastly_changed'] = False
        stab = create_stab(var_name, current)
        ds.put_multi([current, stab])
        return f'{var_name} = {None}'
    parent = ds.get(ds.key(variables_kind, current['parent_id']))
    current['status'] = None
    current['lastly_changed'] = False
    parent['status'] = 'current'
    parent['child_id'] = current.id
    parent['lastly_changed'] = True
    ds.put_multi([current, parent])
    return parent['name'] + ' = ' + parent['value']

def redo():
    last_changed_entity = get_lastly_changed()
    if not last_changed_entity:
        return 'NO COMMANDS'
    var_name = last_changed_entity['name']
    current = get_current(var_name)
    if not current or not current['child_id']:
        return 'NO COMMANDS'
    child = ds.get(ds.key(variables_kind, current['child_id']))
    current['status'] = None
    current['lastly_changed'] = False
    child['status'] = 'current'
    child['lastly_changed'] = True
    ds.put_multi([current, child])
    current = get_current(var_name)

    return current['name'] + ' = ' + current['value']

def exit_program():
    query = ds.query(kind=variables_kind)
    query_iter = query.fetch()
    for entity in query_iter:
        ds.delete(entity)

@app.route('/')
def root():
    return ''

@app.route('/set')
def handle_set_command():
    var_name = request.args.get('name', None)
    var_value = request.args.get('value', None)
    if var_name == None:
        return 'missing name for the variable'
    if var_value == None:
        return 'missing value for the variable'
    set_variable(var_name, var_value)
    return f'{var_name} = {var_value}'

@app.route('/get')
def handle_get_command():
    var_name = request.args.get('name', None)
    if var_name == None:
        return 'missing name for the variable'
    return f'{get_variable(var_name)}'

@app.route('/unset')
def handle_unset_command():
    var_name = request.args.get('name', None)
    if var_name == None:
        return 'missing name for the variable'
    return f'{var_name} = {unset_variable(var_name)}'

@app.route('/numequalto')
def handle_numequalto_command():
    var_value = request.args.get('value', None)
    if var_value == None:
        return 'missing value for the variable'
    return f'{num_equal_to(var_value)}'

@app.route('/undo')
def handle_undo_command():
    return f'{undo()}'

@app.route('/redo')
def handle_redo_command():
    return f'{redo()}'

@app.route('/end')
def handle_end_command():
    exit_program()
    return 'CLEANED'





if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
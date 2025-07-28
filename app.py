#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   app.py
#
# Copyright 2025 AL Haines
#
# v1.1: Fixes an IndexError crash when adding the first command to an empty table.

from flask import Flask, render_template, request, redirect, url_for
from MySql import MySQL
import config

app = Flask(__name__)
db = MySQL(database=config.mysql_config['database'])

@app.route('/')
def index():
    commands = db.get_data("SELECT * FROM dashboard_commands ORDER BY sort_order ASC")
    
    edit_id = request.args.get('edit_id', type=int)
    command_to_edit = None
    if edit_id:
        results = db.get_data("SELECT * FROM dashboard_commands WHERE id = %s", (edit_id,))
        if results:
            command_to_edit = results[0]
            
    return render_template('admin.html', commands=commands, command_to_edit=command_to_edit)

@app.route('/save', methods=['POST'])
def save_command():
    command_id = request.form.get('id')
    key = request.form.get('key')
    name = request.form.get('name')
    command_type = request.form.get('command_type')
    command_string = request.form.get('command_string')
    requires_input = 1 if request.form.get('requires_input') else 0
    quote_input = 1 if request.form.get('quote_input') else 0

    if command_id:
        # UPDATE logic remains the same
        query = """
            UPDATE dashboard_commands SET `key`=%s, name=%s, command_type=%s, 
            command_string=%s, requires_input=%s, quote_input=%s 
            WHERE id=%s
        """
        params = (key, name, command_type, command_string, requires_input, quote_input, command_id)
    else:
        # --- THE CORRECTED LOGIC FOR INSERT ---
        # Get the highest sort_order
        max_sort_order_result = db.get_data("SELECT MAX(sort_order) as max_so FROM dashboard_commands")
        
        # Check if the table was empty. If so, result is [{'max_so': None}]
        # If the query succeeded and returned a result, and that result is not None:
        if max_sort_order_result and max_sort_order_result[0]['max_so'] is not None:
            new_sort_order = max_sort_order_result[0]['max_so'] + 1
        else:
            # If the table is empty, start the sort order at 1.
            new_sort_order = 1
        
        query = """
            INSERT INTO dashboard_commands 
            (`key`, name, command_type, command_string, requires_input, quote_input, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (key, name, command_type, command_string, requires_input, quote_input, new_sort_order)
        
    db.put_data(query, params)
    
    return redirect(url_for('index'))

@app.route('/delete/<int:command_id>', methods=['POST'])
def delete_command(command_id):
    db.put_data("DELETE FROM dashboard_commands WHERE id = %s", (command_id,))
    # After deleting, we should re-sequence the sort_order to prevent gaps
    all_commands = db.get_data("SELECT id FROM dashboard_commands ORDER BY sort_order ASC")
    for i, cmd in enumerate(all_commands, 1):
        db.put_data("UPDATE dashboard_commands SET sort_order = %s WHERE id = %s", (i, cmd['id']))
    return redirect(url_for('index'))

@app.route('/reorder/<int:command_id>/<direction>')
def reorder_command(command_id, direction):
    all_commands = db.get_data("SELECT id, sort_order FROM dashboard_commands ORDER BY sort_order ASC")
    
    try:
        current_index = next(i for i, cmd in enumerate(all_commands) if cmd['id'] == command_id)
    except StopIteration:
        return redirect(url_for('index'))

    if direction == 'up' and current_index > 0:
        other_index = current_index - 1
    elif direction == 'down' and current_index < len(all_commands) - 1:
        other_index = current_index + 1
    else:
        return redirect(url_for('index'))

    cmd1 = all_commands[current_index]
    cmd2 = all_commands[other_index]
    
    db.put_data("UPDATE dashboard_commands SET sort_order = %s WHERE id = %s", (cmd2['sort_order'], cmd1['id']))
    db.put_data("UPDATE dashboard_commands SET sort_order = %s WHERE id = %s", (cmd1['sort_order'], cmd2['id']))
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5052, debug=True)

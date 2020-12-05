#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
database_name = "my_vault" # default name for new databases
default_editor = "nano" # a text editor command to call by default
# use "python" to disable prompt and always use native input
zettel_sort_tags = True # if true - sorts alphabetically
zettel_sort_links = False # if true - sorts alphabetically
search_sort_tags = False # if true - sorts alphabetically
search_sort_titles = False # if true - sorts alphabetically

text_width = 55 #in characters 55...80 should be good

#▒▒▒▒▒▒▒▒▒▒▒▒ CREDITS & LICENCE ▒▒▒▒▒▒▒▒▒▒▒▒▒
# https://writingcooperative.com/zettelkasten-how-one-german-
#	scholar-was-so-freakishly-productive-997e4e0ca125 - idea
# https://zettelkasten.de/introduction/ - method explanation
# https://www.sqlitetutorial.net/sqlite-python/ - db ops
# https://stackoverflow.com/a/63529754 - md links parsing
# Personal thanks to folks from ToughSF who helped me.
# 
# MIT License
# Copyright (c) 2020 Roman Yeremenko
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


#▒▒▒▒▒▒▒▒▒▒▒▒ IMPORTS / CONSTANTS ▒▒▒▒▒▒▒▒▒▒▒▒▒
import os, fnmatch, shutil, pathlib, sqlite3, time, re, random, tempfile
import subprocess, py_compile, gc, textwrap
from sqlite3 import Error

path = os.path.join(os.getcwd(), database_name)
current_db_path = os.path.join(os.getcwd(), database_name + '.db')
zettel_template_name = "_template.md"

marker_title = '[TITLE]'
marker_tags = '[TAGS]'
marker_links = '[ZETTEL LINKS]'
marker_body = '[BODY]'

#A template if you need one
zettel_template = '\n\n\n'.join([marker_title,  
marker_body, marker_tags, marker_links, ''])

#▒▒▒▒▒▒▒▒▒▒▒▒ SQL SCHEMAS ▒▒▒▒▒▒▒▒▒▒▒▒▒
create_meta_table = '''
	CREATE TABLE IF NOT EXISTS meta (
		id integer PRIMARY KEY,
		db_name text NOT NULL, datetime text NOT NULL,
		tot_zettels integer NOT NULL, tot_links integer NOT NULL,
		tot_no_links integer NOT NULL, tot_self_links integer NOT NULL,
		tot_no_bodies integer NOT NULL, tot_no_titles integer NOT NULL
	); '''
create_main_table = '''
	CREATE TABLE IF NOT EXISTS main (
		id integer PRIMARY KEY, z_title text NOT NULL,
		z_path text NOT NULL, z_body text NOT NULL
	); '''
create_links_table = '''
	CREATE TABLE IF NOT EXISTS links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL, z_id_to integer NOT NULL,
		desc text NOT NULL
	); '''
create_no_links_table = '''
	CREATE TABLE IF NOT EXISTS no_links (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_self_links_table = '''
	CREATE TABLE IF NOT EXISTS self_links (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_no_bodies_table = '''
	CREATE TABLE IF NOT EXISTS no_bodies (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_no_titles_table = '''
	CREATE TABLE IF NOT EXISTS no_titles (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_tags_table = '''
	CREATE TABLE IF NOT EXISTS tags (
		id integer PRIMARY KEY, z_id integer NOT NULL, tag text NOT NULL
	); '''
create_taglist_table = '''
	CREATE TABLE IF NOT EXISTS taglist (
		id integer PRIMARY KEY, tag text NOT NULL, UNIQUE ( tag )
	); '''

#INSTERT
insert_main = '''INSERT INTO main ( z_title, z_path, z_body ) VALUES ( ?, ?, ? ) '''
insert_links = '''INSERT INTO links ( z_id_from, z_id_to, desc ) VALUES ( ?, ?, ? ) '''
insert_self_links = '''INSERT INTO self_links ( z_id_from ) VALUES ( ? ) '''
insert_no_links = '''INSERT INTO no_links ( z_id_from ) VALUES ( ? ) '''
insert_no_bodies = '''INSERT INTO no_bodies ( z_id_from ) VALUES ( ? ) '''
insert_no_titles = '''INSERT INTO no_titles ( z_id_from ) VALUES ( ? ) '''
insert_tags = '''INSERT INTO tags ( z_id, tag ) VALUES ( ?, ? ) '''
insert_taglist = '''INSERT OR IGNORE INTO taglist ( tag ) VALUES ( ? ) ''' 
insert_meta = '''
	INSERT INTO meta (
		db_name, datetime, tot_zettels, tot_links,
		tot_no_links, tot_self_links, tot_no_bodies, tot_no_titles
	) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? ) ''' #add tags num

#SELECT
select_meta_all = "SELECT * FROM meta"

select_main_id = "SELECT * FROM main WHERE id = ?"
select_main_z_path = "SELECT * FROM main WHERE z_path = ?"
select_main_all = "SELECT * FROM main"
select_main_z_title_like = "SELECT * FROM main WHERE z_title LIKE ? "
select_main_z_body_like = "SELECT * FROM main WHERE z_body LIKE ? "
select_main_z_path_like = "SELECT * FROM main WHERE z_path LIKE ? "

select_self_links_all = "SELECT * FROM self_links"
select_no_links_all = "SELECT * FROM no_links"
select_no_bodies_all = "SELECT * FROM no_bodies"
select_no_titles_all = "SELECT * FROM no_titles"

select_taglist_id = "SELECT * FROM taglist WHERE id = ?"
select_taglist_all = "SELECT * FROM taglist"
select_taglist_tag_like = "SELECT * FROM taglist WHERE tag LIKE ? "

select_tags_z_id = "SELECT * FROM tags WHERE z_id = ?"
select_tags_all = "SELECT * FROM tags"
select_tags_all_dist = "SELECT DISTINCT * FROM tags"

select_tags_tag = "SELECT * FROM tags WHERE tag = ? "

select_links_all = "SELECT * FROM links"
select_links_z_id_from = "SELECT * FROM links WHERE z_id_from = ?"
select_links_z_id_to = "SELECT * FROM links WHERE z_id_to = ?"

#UPDATE
update_main_z_body = 'UPDATE main SET z_body = ? WHERE id = ?'
update_main_z_title = 'UPDATE main SET z_title = ? WHERE id = ?'

update_links_desc = 'UPDATE links SET desc = ? WHERE id = ?'

update_tags_tag = 'UPDATE tags SET tag = REPLACE(tag, ?, ? )'

#DELETE
delete_meta_all = "DELETE FROM meta"

delete_main_id = "DELETE FROM main WHERE id = ?"

delete_taglist_all = "DELETE FROM taglist"

delete_self_links_all = "DELETE FROM self_links"
delete_no_links_all = "DELETE FROM no_links"
delete_no_titles_all = "DELETE FROM no_titles"
delete_no_bodies_all = "DELETE FROM no_bodies"

delete_tags_z_id = "DELETE FROM tags WHERE z_id = ?"
delete_tags_tag = "DELETE FROM tags WHERE tag = ?"

delete_links_z_id_from = "DELETE FROM links WHERE z_id_from = ?"
delete_links_z_id_to = "DELETE FROM links WHERE z_id_to = ?"

#▒▒▒▒▒▒▒▒▒▒▒▒ WRITING DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def write_no_titles(z_id): add_to_db([z_id], insert_no_titles, current_db_path)
def write_no_bodies(z_id): add_to_db([z_id], insert_no_bodies, current_db_path)
def write_no_links(z_id): add_to_db([z_id], insert_no_links, current_db_path)
def write_self_titles(z_id): add_to_db([z_id], insert_self_links, current_db_path)
	
def write_zettel(z_title, z_path, z_body):
	z_id = add_to_db([z_title, z_path, z_body], insert_main, current_db_path)
	return z_id #regurns only last id

def write_tags(z_id, tags):
	entry_list = []
	for tag in tags: #swap tag ID with z_id
		entry_list.append((z_id, tag[1]))
	incr_add_to_db(entry_list, insert_tags, current_db_path)

def write_taglist_tag(tags):
	t_id = incr_add_to_db(tags, insert_taglist, current_db_path)
	return t_id #regurns only last id
	
def write_links_from(z_id, zettels):
	entry_list = []
	if not zettels:
		print_no_links_for_writing(); p(); return
	for zettel in zettels:
		desc = 'Link to '+zettel[1]+' because...'
		entry_list.append((z_id, zettel[0], desc))
	incr_add_to_db(entry_list, insert_links, current_db_path)
	
#▒▒▒▒▒▒▒▒▒▒▒▒ READING DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def read_links_all(): return query_db(None, select_links_all, current_db_path)
def read_links_z_id_from(z_id): return query_db(z_id, select_links_z_id_from, current_db_path)
def read_links_z_id_to(z_id): return query_db(z_id, select_links_z_id_to, current_db_path)

def read_taglist_id(id): return query_db(id, select_taglist_id, current_db_path)[0] #only one tag
def read_taglist_all(): return query_db(None, select_taglist_all, current_db_path)
def read_taglist_tags_like(name): return query_db('%'+name+'%', select_taglist_tag_like, current_db_path)

def read_tags_all(): return query_db(None, select_tags_all, current_db_path)
def read_tags_all_dist(): return query_db(None, select_tags_all_dist, current_db_path)
def read_tags_z_id(z_id): return query_db(z_id, select_tags_z_id, current_db_path)

def read_tags_tag(tag): return query_tags(tag, current_db_path)

def read_main_id(id): return query_db(id, select_main_id, current_db_path)[0] #only one zettel
def read_main_z_path(name): return query_db(name, select_main_z_path, current_db_path)
def read_main_all(): return query_db(None, select_main_all, current_db_path)
def read_main_z_title_like(name): return query_db('%'+name+'%', select_main_z_title_like, current_db_path)
def read_main_z_path_like(name): return query_db('%'+name+'%', select_main_z_path_like, current_db_path)
def read_main_z_body_like(name): return query_db('%'+name+'%', select_main_z_body_like, current_db_path)

def read_meta_all(db_name): return query_db(None, select_meta_all, db_name)[0] #only one zettel

#▒▒▒▒▒▒▒▒▒▒▒▒ REWRITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
#called by 'edit' functions
def rewrite_main_z_body(id, text):
	add_to_db([text, id], update_main_z_body, current_db_path)
	
def rewrite_main_z_title(id, title):
	add_to_db([title, id], update_main_z_title, current_db_path)

def rewrite_links_from(z_id, zettels): 
	remove_links_from(z_id)
	write_links_from(z_id, zettels)
	
def rewrite_zettel_tags(z_id, tags): #tags attached to zettel
	remove_tags_z_id(z_id)
	write_tags(z_id, tags)
	rescan_taglist() #might contain new tags or remove old
	
def rewrite_tags_tag(new_tag, old_tag): 
	add_to_db([old_tag, new_tag], update_tags_tag, current_db_path)
	rescan_taglist() #reflect changes

#▒▒▒▒▒▒▒▒▒▒▒▒ REMOVE OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def remove_links_from(z_id): #after zettel removal, or optional
	delete_from_db(z_id, delete_links_z_id_from, current_db_path)
	
def remove_links_to(z_id): #after zettel removal, or optional
	delete_from_db(z_id, delete_links_z_id_to, current_db_path)
	
def remove_tags_z_id(z_id): #after zettel removal, or optional
	delete_from_db(z_id, delete_tags_z_id, current_db_path)
	rescan_taglist() #might remove all tag instances
	
def remove_tags_tag(name):
	delete_from_db(name, delete_tags_tag, current_db_path)
	rescan_taglist() #removes all instances

def remove_main_id(id):
	delete_from_db(id, delete_main_id, current_db_path)
	
#▒▒▒▒▒▒▒▒▒▒▒▒ REBUILD OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def rescan_taglist(): #after tag edit
	tags = []
	delete_from_db(None, delete_taglist_all, current_db_path)
	for entry in read_tags_all_dist():
		tags.append((entry[2],)) #need only names
	incr_add_to_db(tags, insert_taglist, current_db_path)
	
def rescan_meta(): #only when checking
	delete_from_db(None, delete_meta_all, current_db_path)
	delete_from_db(None, delete_self_links_all, current_db_path)
	delete_from_db(None, delete_no_links_all, current_db_path)
	delete_from_db(None, delete_no_titles_all, current_db_path)
	delete_from_db(None, delete_no_bodies_all, current_db_path)
	dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
	zettels = read_main_all()
	links = read_links_all()
	tags = read_tags_all()
	tot_zettels = len(zettels)
	tot_links = len(links)
	tot_no_bodies = 0
	tot_no_titles = 0
	tot_no_links = 0
	tot_self_links = 0
	for zettel in zettels:
		z_id = zettel[0]
		if not zettel[1]: 
			tot_no_titles += 1
			write_no_titles(z_id)
		if not zettel[3]: 
			tot_no_bodies += 1
			write_no_bodies(z_id)
		if not read_links_z_id_from(z_id) and not read_links_z_id_to(z_id): 
			tot_no_links += 1
			write_no_links(z_id)
	for link in links:
		if link[1] == link[2]: 
			tot_self_links += 1
			write_self_titles(link[1])
	metadata = [
		database_name, #
		dt_str, #
		tot_zettels, #
		tot_links, #
		tot_no_links, #
		tot_self_links, #
		tot_no_bodies, #
		tot_no_titles, #
	]
	add_to_db(metadata, insert_meta, current_db_path)

#▒▒▒▒▒▒▒▒▒▒▒▒ ZETTEL / TAG WRITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def write_num_not_empty(type, prompt_str):
	while True:
		num = c_prompt(prompt_str)
		try: 
			if type == 'int': num = int(num); return num
			elif type == 'float': num = float(num); return num
			else: print_wrong_num_type(); p()
		except: print_num_wrong_input()
		
def write_not_empty(inject_text, flag, allow_exit):
	name = '';
	while not name: 
		if not flag == 'prompt': name = write_with_editor(inject_text)
		else: name = write_fallback(inject_text)
		name = parse_off_comments(name)
		if name =='': 
			if not allow_exit:
				print_abort_writing()
				inp = c_prompt('')
				if inp == 'qm': main_menu()
			else: 
				print_abort_writing_quit_allowed()
				inp = c_prompt('')
				if inp == 'qm': main_menu()
				elif inp == 'q': return name
	return name

def write_with_editor(inject_text):
	def write_ext(option, inject_text):
		written = ''
		with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
			if inject_text: 
				try: tf.write(inject_text)
				except TypeError: tf.write(inject_text.encode("utf-8"))
				finally: tf.flush()
			try: 
				subprocess.call([option, tf.name])
				tf.seek(0); written = tf.read().decode("utf-8")
				return written.strip()
			except: 
				print_no_default_editor(option); p(); 
				return write_fallback(inject_text)
	#BEGIN
	if default_editor == 'python': return write_fallback(inject_text)
	else: return write_ext(default_editor, inject_text)

def write_fallback(inject_text):
	print_fallback_editor(inject_text)
	return s_prompt('enter text')
	
def make_new_zettel():
	comment = '# Enter the zettel title below\n'
	z_title = write_not_empty(comment, flag=None, allow_exit=False)
	comment = '# Enter the zettel text body below\n'
	z_body = write_not_empty(comment, flag=None, allow_exit=False)
	print_zettels_select(); p()
	zettels_linked = zettel_picker(None)
	print_tags_select(); p()
	tags = tag_picker()
	#generate filename for export feature
	path_length = 30
	z_path = z_title
	if len(z_path) > path_length: z_path = z_path[0:path_length]
	z_path = z_path.strip().replace(' ', '_')
	z_path = re.sub(r'(?u)[^-\w.]', '_', z_path) 
	z_path += '.md'
	z_id = write_zettel(z_title, z_path, z_body)
	write_tags(z_id, tags)
	write_links_from(z_id, zettels_linked)
	#update meta
	#find it and enter ops sub menu
	print_new_zettel_preview(); p()
	new_zettel = read_main_id(z_id)
	zettel_ops(new_zettel, editor_select_mode=False)
	return new_zettel

def make_new_tag(old_tag):
	comment = '# Write a new tag name below\n'
	if old_tag: #updating an old one
		new_tag = write_not_empty(comment+old_tag, flag=None, allow_exit=False)
		rewrite_tags_tag(new_tag, old_tag)
		try: t_id = read_taglist_tags_like(new_tag)[0]
		except IndexError: print_detached_tag_rename(); p(); main_menu()
	else: #making a new one
		new_tag = write_not_empty(comment, flag=None, allow_exit=False)
		t_id = write_taglist_tag([(new_tag,)])
	return (t_id, new_tag)

#▒▒▒▒▒▒▒▒▒▒▒▒ EDITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def zettel_picker(current_z_id): #add ops to edit the list properly
	zettels = [] 
	try: zettels += search_zettels(current_z_id, editor_select_mode=True)
	except TypeError: pass
	return zettels
	
def tag_picker(): #add ops to edit the list properly
	tags = [] 
	try: tags += search_tags(editor_select_mode=True)
	except TypeError: pass
	return tags
	
def edit_main_z_title(z_id):
	z_title = read_main_id(z_id)[1]
	comment = '# Enter the new zettel title below\n'
	new_title = write_not_empty(comment+z_title, flag=None, allow_exit=False)
	rewrite_main_z_title(z_id, new_title)
	
def edit_main_z_body(z_id):
	comment = '# Enter the new zettel text body below\n'
	z_body = read_main_id(z_id)[3]
	new_body = write_not_empty(comment+z_body, flag=None, allow_exit=False)
	rewrite_main_z_body(z_id, new_body)
	
def edit_links_z_id_from(z_id):
	zettels = zettel_picker(z_id)
	rewrite_links_from(z_id, zettels)
	
def edit_tags_z_id(z_id):
	tags = tag_picker()
	rewrite_zettel_tags(z_id, tags)

def delete_zettel(z_id):
	print('delete zettel')
	remove_main_id(z_id)
	remove_links_from(z_id)
	remove_links_to(z_id)
	remove_tags_z_id(z_id)
	rescan_taglist()
	p()

#▒▒▒▒▒▒▒▒▒▒▒▒ ANALYZE OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def review(): #make an actualcheck
	rescan_meta()
	print_db_meta(current_db_path)
	errors = False
	if not os.path.isfile(current_db_path): print_no_db_warn(); return
	if print_zettels_warnings(None, select_no_titles_all): print_no_titles_warn(); errors = True
	if print_zettels_warnings(None, select_no_bodies_all): print_no_bodies_warn(); errors = True
	if print_zettels_warnings(None, select_no_links_all): print_no_links_warn(); errors = True
	if print_zettels_warnings(None, select_self_links_all): print_self_links_warn(); errors = True
	if not errors: print_check_passed()
	p()

#▒▒▒▒▒▒▒▒▒▒▒▒ MENU OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def zettel_ops(zettel, editor_select_mode):
	def zettel_edit_ops(zettel, z_id):
		print_whole_zettel(zettel); print_zettel_edit_ops()
		inp = c_prompt('')
		if inp == 'n': edit_main_z_title(z_id)
		elif inp == 'b': edit_main_z_body(z_id)
		elif inp == 'l': edit_links_z_id_from(z_id)
		elif inp == 't': edit_tags_z_id(z_id)
		elif inp == 'd': delete_zettel(z_id); main_menu()
	###
	def zettel_extra_ops(zettel, z_id):
		print_whole_zettel(zettel); print_zettel_extra_ops()
		inp = c_prompt('')
		if inp == 'nlt': follow_n_depth_links_z_id('outgoing', z_id)
		elif inp == 'nlb': follow_n_depth_links_z_id('incoming', z_id)
		elif inp == 'nal': follow_n_depth_links_z_id('both', z_id)
	#BEGIN
	z_id = zettel[0]; z_title = zettel[1]; z_body = zettel[3]
	if not editor_select_mode: print_whole_zettel(zettel); print_zettel_ops() #init
	else: print_whole_zettel(zettel); print_zettel_ops_lim() #init
	while True:
		inp = c_prompt('')
		if not editor_select_mode:
			if inp == '': return zettel
			elif inp == 'lt': follow_links_z_id('from', z_id)
			elif inp == 'lb': follow_links_z_id('to', z_id)
			elif inp == 'x': zettel_extra_ops(zettel, z_id)
			elif inp == 'e': zettel_edit_ops(zettel, z_id)
			elif inp == 'qm': main_menu()
		else:
			if inp == '': return zettel
			elif inp == 'qm': main_menu()
		zettel = read_main_id(z_id) #refresh to reflect changes
		print_whole_zettel(zettel); 
		if not editor_select_mode: print_zettel_ops()
		else: print_zettel_ops_lim()
		
def tag_ops(tag, editor_select_mode):
	if not editor_select_mode:
		tag_id = tag[0];
		result = list_by_tag(tag_id) #if it returns - tag is good
		zettels = result[0]; titles = result[1]; listed_tag = result[2]
		print_tag_info(titles, listed_tag); print_tag_ops()
	else: return tag
	while not editor_select_mode:
		inp = c_prompt('')
		if inp == '': return tag
		elif inp =='i': 
			print_zettels_under_tag(titles, tag);
			zettel_select_ops(zettels, editor_select_mode); #return tag
		elif inp == "e": new_tag = make_new_tag(tag[1]); return new_tag
		elif inp == 'qm': main_menu()
		print_tag_info(titles, listed_tag); print_tag_ops()
	
def zettel_select_ops(zettels, editor_select_mode): #when zettel list provided
	print_select_zettel_ops()
	zettel = None
	inp = c_prompt('')
	try: 
		zettel = zettels[int(inp)-1]
		zettel_ops(zettel, editor_select_mode)
	except (ValueError, IndexError): pass
	if inp == '': return True
	elif inp == 'qm': main_menu()

def zettel_search_ops(s):
	print_search_zettel_ops()
	inp = c_prompt('')
	try: 
		s['found'] = s['entries'][int(inp)-1]; return s
	except (ValueError, IndexError): pass
	finally:
		if inp == 'ew': 
			s['inp'] = ''; comment = '# Edit your search phrase below\n'
			s['name'] = write_not_empty(comment+s['name'], '', allow_exit=True)
		elif inp == 'cw':  s['inp'] = ''; s['name'] = ''; 
		elif inp == 'ct': s['inp'] = ''; s['tags_names'] = []; s['tags'] = []; 
		elif inp == 't': s['inp'] = ''; s['tags'] = search_tags(editor_select_mode=True)
		elif inp == 'n': make_new_zettel()
		elif inp == 'q': s['stop'] = True
		elif inp == 'qm': main_menu()
	return s
	
def tag_search_ops(s, editor_select_mode):
	if editor_select_mode: print_search_tag_edit()
	else: print_search_tag_view()
	inp = c_prompt('')
	try: 
		s['found'] = s['entries'][int(inp)-1]; return s
	except (ValueError, IndexError): pass
	finally:
		if inp == 'ew': 
			s['inp'] = ''; comment = '# Edit your search phrase below\n'
			s['name'] = write_not_empty(comment+s['name'], '', allow_exit=True)
		elif inp == "cw": s['name'] = ''; s['inp'] = ''; s['entries'] = read_taglist_all() #reset
		elif inp == "q": s['stop'] = True
		elif inp == 'qm': main_menu()
		if editor_select_mode and inp == "n": 
			s['found'] = make_new_tag(None)
	return s

def main_menu():
	print_main_ops()
	while True:
		inp = c_prompt('MENU')
		if inp == "i": print_db_meta(current_db_path); p()
		elif inp == "n": make_new_zettel();
		elif inp == "z": search_zettels(None, editor_select_mode=False); 
		elif inp == "t": search_tags(editor_select_mode=False); 
		elif inp == "r": review();
		elif inp == "init": init_new_db();
		elif inp == "temp": make_template();
		elif inp == "test": make_test_zettels();
		elif inp == "import": import_zettels();
		elif inp == "compile": compile_myself();
		elif inp == "git": git_menu(); 
		elif inp == "q": quit()
		print_main_ops()

def git_menu():
	print_git_ops()
	while True:
		inp = c_prompt('GIT')
		print_git_ops()
		if inp == "": git_info()
		elif inp == "l": git_log_f()
		elif inp == "s": git_status()
		elif inp == "c": git_commit_f()
		elif inp == "p": git_push()
		elif inp == "r": git_revert_f()
		elif inp == "ha": git_reset_hard_f()
		elif inp == "u": git_launch_gitui()
		elif inp == "q": break
		
#▒▒▒▒▒▒▒▒▒▒▒▒ SEARCH OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def follow_n_depth_links_z_id(flag, z_id):
	def get_zettels(flag, ids, found_zettels):
		ids_next = []; linked_zettels = [];
		for z_id in ids:
			if flag == 'outgoing': linked_zettels += list_by_links_z_id_from(z_id)[0]
			elif flag == 'incoming': linked_zettels += list_by_links_z_id_to(z_id)[0]
			elif flag == 'both': 
				linked_zettels += list_by_links_z_id_from(z_id)[0]
				linked_zettels += list_by_links_z_id_to(z_id)[0]
		for zettel in linked_zettels:
			if not zettel in found_zettels: #prevent dupes
				#print(zettel);
				#print(found_zettels); p()
				nth_z_id = zettel[0]
				found_zettels.append(zettel)
				ids_next.append(nth_z_id)
			else: pass
		return (found_zettels, ids_next)
	###
	def find_n_depth_links_z_id(flag, z_id, depth):
		current_zettel = read_main_id(z_id)
		ids = [z_id]; found_zettels = [current_zettel]; n = 0 #init
		while n < depth and ids:
			result = get_zettels(flag, ids, found_zettels)
			found_zettels = result[0]; ids = result[1]
			n += 1
		return found_zettels
	#BEGIN
	depth = write_num_not_empty('int', 'how many levels of links to open?')
	found_zettels = find_n_depth_links_z_id(flag, z_id, depth)
	print_many_zettels(found_zettels);p()
		
def follow_links_z_id(flag, z_id):
	z_title = read_main_id(z_id)[1]
	if flag =='to': result = list_by_links_z_id_to(z_id)
	if flag =='from': result = list_by_links_z_id_from(z_id)
	zettels = result[0]; titles = result[1]
	while True:
		print_zettels_links_z_id(flag, titles, z_title)
		if zettel_select_ops(zettels, editor_select_mode=False): return
	
def search_zettels(current_z_id, editor_select_mode):
	def find_zettel(s, prev_found, editor_select_mode):
		s = zettel_filter_lists(s) #init
		while True:
			if s['inp'] and s['inp'] != ':': 
				s['name_prev'] = s['name'] #store prev. step
				s['name'] += s['inp']
				s = zettel_filter_lists(s) #filter entries
				s['found'] = print_list_or_return(s['entries'])
				if s['found']: s['exact'] = True; return s
				if s['stop']: return s
				s['inp'] =''; continue #refresh keywords
			if s['inp'] == ':': 
				print_list_or_return(s['entries']) #print over prompt
				print_zettel_search_stats(s['tags_names'], s['name'])
				if editor_select_mode: print_selected(prev_found, 1) #if in select mode
				s = zettel_search_ops(s); 
				s = zettel_filter_lists(s) #filter entries
				if s['found']: s['exact'] = False; return s
				if s['stop']: return s
				s['inp'] =''; continue #refresh tags
			print_list_or_return(s['entries']) #print
			print_zettel_search_stats(s['tags_names'], s['name'])
			if editor_select_mode: print_selected(prev_found, 1) #if in select mode
			s['inp'] = s_prompt("enter text (':' - options)")
	###
	def zettel_filter_lists(s):
		s['entries'] = []; #keyword search
		s['entries_title'] = read_main_z_title_like(s['name'])
		#suspend this feature for now
		#s['entries_body'] = read_main_z_body_like(s['name'])
		s['entries'] = s['entries_title'] #+ s['entries_body']
		s['entries'] = list(dict.fromkeys(s['entries'])) #dedup
		for tag in s['tags']:
			s['tags_names'].append(tag[1])
		s['tags_names'] = list(dict.fromkeys(s['tags_names'])) #dedup
		if len(s['tags_names']) > 1: #if many tags
			zettels_groups = []; intersected = []
			for tag in s['tags_names']: #find zettel groups for each tag
				group = []
				tagged = read_tags_tag(tag)
				for tagged_entry in tagged:
					found_id = tagged_entry[1]
					zettel = read_main_id(found_id)
					group.append(zettel)
				zettels_groups.append(group) #a list of lists
			for group in zettels_groups: #incrementally intersect
				s['entries'] = list(set(s['entries']) & set(group))
		elif len(s['tags_names']) == 1: #if only one tag
			tag = s['tags_names'][0]; s['entries_tag'] = []
			tagged = read_tags_tag(tag)
			for tagged_entry in tagged:
				found_id = tagged_entry[1]
				zettel = read_main_id(found_id)
				s['entries_tag'].append(zettel)
			s['entries'] = list(set(s['entries']).intersection(s['entries_tag'] ))
		return s
	#BEGIN
	entries = []
	s = {'found': None, 'exact': False, 'name': '', 'inp': '', 'entries_tag': [], 'name_prev': '',
		'tags_names': [], 'entries': [], 'entries_title': [], 'entries_body': [], 'tags': [], 'stop': False}
	while True:
		s = find_zettel(s, entries, editor_select_mode)
		if s['stop']: break #must be first
		if s['found'] and not s['exact']: 
			result = zettel_ops(s['found'], editor_select_mode) #may be edited
			if editor_select_mode and current_z_id != result[0]: 
				entries.append(result)
				entries = list(dict.fromkeys(entries)) #dedup
			elif editor_select_mode and current_z_id == result[0]:
				print_picking_same_zettel(); p()
			s['found'] = None; s['inp'] = '' #keep searching if not exact found
		if s['exact']: 
			result = zettel_ops(s['found'], editor_select_mode) #may be edited
			if editor_select_mode and current_z_id != result[0]: 
				entries.append(result)
				entries = list(dict.fromkeys(entries)) #dedup
			elif editor_select_mode and current_z_id == result[0]:
				print_picking_same_zettel(); p()
			s['found'] = None; s['inp'] = ''; s['name'] = s['name_prev'] #roll back to resume narrowed search
	return entries

def search_tags(editor_select_mode): #must be passed in
	def find_tags(s, prev_found, editor_select_mode): #must be passed in
		s['entries'] = read_taglist_tags_like(s['name']) #init
		s['found'] = print_list_or_return(s['entries'])
		while True:
			if s['inp'] and s['inp'] != ':': 
				s['name_prev'] = s['name'] #store prev. step
				s['name'] += s['inp']
				s['entries'] = read_taglist_tags_like(s['name'])
				s['found'] = print_list_or_return(s['entries'])
				if s['found']: s['exact'] = True; return s
				if s['stop']: return s
			elif s['inp'] == ':': 
				print_list_or_return(s['entries']) #print over prompt
				print_tag_search_stats(s['name'])
				if editor_select_mode: print_selected(prev_found, 1)
				s = tag_search_ops(s, editor_select_mode); 
				if s['found']: s['exact'] = False; return s
				if s['stop']: return s
			print_list_or_return(s['entries']) #print
			print_tag_search_stats(s['name'])
			if editor_select_mode: print_selected(prev_found, 1)
			s['inp'] = s_prompt("enter text (':' - options)")
		
	#BEGIN
	entries = []
	s = {'found': None, 'exact': False, 'name': '', 'inp': '', 'name_prev': '', 
		'entries': [], 'stop': False}
	while True:
		s = find_tags(s, entries, editor_select_mode)
		if s['stop']: break
		if s['found'] and not s['exact']: 
			result = tag_ops(s['found'], editor_select_mode)
			if editor_select_mode: 
				entries.append(result)
				entries = list(dict.fromkeys(entries)) #dedup
			s['found'] = None; s['inp'] = '' #keep searching if not exact found
		if s['exact']:
			result = tag_ops(s['found'], editor_select_mode)
			if editor_select_mode: 
				entries.append(result)
				entries = list(dict.fromkeys(entries)) #dedup
			s['found'] = None; s['inp'] = ''; s['name'] = s['name_prev'] #roll back to resume narrowed search
	return entries

#▒▒▒▒▒▒▒▒▒▒▒▒ FORMATTING ▒▒▒▒▒▒▒▒▒▒▒▒▒
if text_width < 30: print('minimal text width value is 30'); text_width = 30
in_tags = ' tags:   '
in_links_out = ' └ to:   '
in_links_in = ' └ by:   '
indent = '         '; ph = '...'
right_indent = 4; ml = 3
tw_tags = textwrap.TextWrapper(text_width-right_indent, 
	initial_indent=in_tags, subsequent_indent=indent,
	placeholder=ph, max_lines=ml)
tw_links_out = textwrap.TextWrapper(text_width-right_indent, 
	initial_indent=in_links_out, subsequent_indent=indent,
	placeholder=ph, max_lines=ml)
tw_links_in = textwrap.TextWrapper(text_width-right_indent, 
	initial_indent=in_links_in, subsequent_indent=indent,
	placeholder=ph, max_lines=ml)
tw = textwrap.TextWrapper(text_width)
tw_w = textwrap.TextWrapper(text_width-1, initial_indent=' ', subsequent_indent=' ', replace_whitespace=False)
tw_i = textwrap.TextWrapper(text_width, subsequent_indent=indent)


#▒▒▒▒▒▒▒▒▒▒▒▒ PRINT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
#DB ERROR CHECK
def print_no_db_warn():
	divider()
	print(tw.fill('''
no database matching the name provided in this script
check the name in the script header, or import or
initiate the database via respective commands
'''.strip()))
	
def print_no_titles_warn(): 
	print(''); print(tw.fill('''
there are zettels without titles listed above, inspect
'''.strip()))

def print_no_bodies_warn(): 
	print(''); print(tw.fill('''
there are zettels without text listed above, fill them
'''.strip()))

def print_no_links_warn(): 
	print(''); print(tw.fill('''
there are unlinked zettels listed above, link them
'''.strip()))

def print_self_links_warn(): 
	print(''); print(tw.fill('''
there are zettels linking to themselves listed above
'''.strip()))
	
def print_invalid_links_warn():
	print(''); print(tw.fill('''
there are corrupt links in your zettels this error should occur
after importing .md zettels which is why you shall fix the links
in your .md files and then re-import them to database again
optionally, you may ignore this warning and those links will not
be included to the database
'''.strip()))

def print_dupe_links_warn():
	print(''); print(tw.fill('''
there are duplicate links in your zettels this error should occur
after importing .md zettels which is why you shall fix the links
in your .md files and then re-import them to database again
optionally, you may ignore this warning and those links will not
be included to the database
'''.strip()))
	
def print_check_passed(): 
	divider(); 
	print(tw.fill('''
all good, no corrupt links or unlinked zettels
'''.strip()))

def print_invalid_links(entries):
	same_zettel = False; id_prev = None; num = 1
	divider()
	for entry in entries:
		z_id = entry[0]; z_title = entry[1]; z_path = entry[2]; 
		invalid_link_name = entry[3]
		if z_id == id_prev: same_zettel = True
		if same_zettel:
			print(tw_i.fill('   └─{0}'.format(invalid_link_name)))
			same_zettel = False
		else:
			print()
			print(tw_i.fill('{0}. id: {1}, {2}'.format(str(num), str(z_id), z_title)))
			print(tw_i.fill('   file: {0}'.format(z_path)))
			print(tw_i.fill('   corrupt links:'))
			print(tw_i.fill('   └─{0}'.format(invalid_link_name)))
			num += 1
		id_prev = z_id
	print_invalid_links_warn()
	
def print_dupe_links(entries):
	same_zettel = False; id_prev = None; num = 1
	divider()
	for entry in entries:
		z_id = entry[0]; z_title = entry[1]; z_path = entry[2]; 
		invalid_link_name = entry[3]; link_desc = entry[4]
		if z_id == id_prev: same_zettel = True
		if same_zettel:
			print(tw_i.fill('   └─{0} ░ {1}'.format(invalid_link_name, link_desc)))
			same_zettel = False
		else:
			print()
			print(tw_i.fill('{0}. id: {1}, {2}'.format(str(num), str(z_id), z_title)))
			print(tw_i.fill('   file: {0}'.format(z_path)))
			print(tw_i.fill('   duplicate links:'))
			print(tw_i.fill('   └─{0} ░ {1}'.format(invalid_link_name, link_desc)))
			num += 1
		id_prev = z_id
	print_dupe_links_warn()
		
def print_zettels_warnings(query, exec_str): #for other kinds of errors
	entries = query_db(query, exec_str, current_db_path); num = 1
	if entries == []: return False;
	divider()
	for entry in entries:
		z_id = entry[1]; z_title = read_main_id(z_id)[1]
		print(tw_i.fill('{0}. id: {1}, {2}'.format(str(num), str(z_id), z_title)))
		num += 1
	return True
	
#DB MAKING
def print_init_new_db():
	cl_divider()
	print(tw.fill('''
you are about to create an empty database, the new database 
will be created in current folder please enter a unique name for it
'''.strip()))

def print_db_exists(): 
	cl_divider()
	print(tw.fill('''
a database like this already exists, aborting
'''.strip()))

def print_importing_warn():
	cl_divider()
	print(tw.fill('''
you are about to import your .md zettels to database
make sure the folder with zettels is in the same
directory as this application
folders with nested sub-folders are not supported
that will lead to corrupted links
'''.strip()))
	
def print_importing_succeeded(database_name, t):
	divider()
	print(tw.fill('''
success, database built in: {0} s,
to use the database rename file to match: {1}.db
this is the name given in the application options
do not forget to review the database for errors
'''.format(t, database_name).strip()))
	
def print_importing_failed():
	divider()
	print(tw.fill('''
wrong folder name, aborting...
'''.strip()))
	
#TEST
def print_test_warn():
	cl_divider()
	print(tw.fill('''
make sure you have backed up your journal folder
this will generate a batch of zettel .md cards in it
you will have to import them back into a database
'''.strip()))
	
def print_made_tests():
	cl_divider()
	print(tw.fill('''
generated a number of test zettels
don't forget to import them into the database
'''.strip()))

#WRITING GENERAL 
def print_num_wrong_input(): 
	cl_divider(); 
	print(tw.fill('''
make sure you enter numbers
'''.strip()))

def print_wrong_num_type(): 
	cl_divider(); 
	print(tw.fill('''
wrong numeric type supplied
'''.strip()))

def print_abort_writing():
	cl_divider()
	print(tw.fill('no text was written, you can try again or abort'))
	print(tw_i.fill('() - resume writing'))
	print_qm()
	
def print_abort_writing_quit_allowed():
	cl_divider()
	print(tw.fill('no text was written, you can try again or abort'))
	print(tw_i.fill('() - resume writing'))
	print_q()
	print_qm()
	
def print_no_default_editor(option): 
	cl_divider(); 
	print(tw.fill('unable to use default editor: {0}'.format(option)))
	print(tw.fill('will switch to standard python input'))
	
def print_fallback_editor(inject_text): 
	if inject_text:
		divider()
		for line in inject_text.splitlines():
			print(tw_w.fill('{0}'.format(line)))

def print_no_links_for_writing():
	cl_divider(); 
	print(tw.fill('no links provided for writing'))
	
#ZETTEL WRITING / READING
def print_zettels_select():
	cl_divider(); 
	print(tw.fill('select zettels that you want to LINK to'))
	
def print_tags_select():
	cl_divider()
	print(tw.fill('''
select a suitable TAG for your zettel you can either
search for existing tag or write a new one if no suitable found
'''.strip()))

def print_title_select():
	cl_divider()
	print(tw.fill('''
select a suitable TITLE for your zettel, it must not be empty
'''.strip()))

def print_body_select():
	cl_divider()
	print(tw.fill('''
enter the TEXT BODY of the zettel, it must not be empty
'''.strip()))

def print_new_zettel_preview():
	cl_divider()
	print(tw.fill('''
you can now preview and edit your new zettel
'''.strip()))

def print_whole_zettel(zettel):
	cl_divider()
	print_single_zettel(zettel)
	
def print_many_zettels(zettels):
	cl()
	for zettel in zettels:
		divider()
		print_single_zettel(zettel)

def print_single_zettel(zettel):
	try: title = zettel[1]; body = zettel[3]
	except IndexError: 
		title ='<no title / corrupted title>';
		body ='<no text body / corrupted text body>'
	tags = read_tags_z_id(zettel[0]) #tags
	tags_str = str_from_list(zettel_sort_tags, tags, 2, '', ' ░ ', '').strip()
	links_out = read_links_z_id_from(zettel[0]) #lnks
	links_in = read_links_z_id_to(zettel[0]) 
	linked_zettels_out = []; linked_zettels_in = []
	for link in links_out:
		linked_zettel = read_main_id(link[2])
		linked_zettels_out.append(linked_zettel)
	for link in links_in:
		linked_zettel = read_main_id(link[1])
		linked_zettels_in.append(linked_zettel)
	links_out_str = str_from_list(zettel_sort_links, linked_zettels_out, 1, '', ' ░ ', '').strip()
	links_in_str = str_from_list(zettel_sort_links, linked_zettels_in, 1, '', ' ░ ', '').strip()
	#printing
	print_header('░', title), print() 
	for line in body.splitlines():
		print(tw_w.fill('{0}'.format(line)))
	print(); print(tw_tags.fill(tags_str)); print()
	if links_out or links_in: print(' linked')
	if links_out: print(tw_links_out.fill(links_out_str)); print()
	if links_in: print(tw_links_in.fill(links_in_str)); print()
	
def print_header(sym, name):
	if len(name) < text_width: 
		l=(text_width - len(name)-2)//2; 
		name=sym*l+' '+name+' '+sym*l;
		if len(name) < text_width: name += sym #compensate
		print(name)
	else: 
		print(tw.fill(name))
		print(sym*text_width)

#SEARCHING ZETTEL
def print_zettel_search_stats(tags, name):
	s = str_from_list(False, tags, None, '', ' | ', '').strip()
	print(tw_i.fill('filter by tag: {0}'.format(s)))
	print(tw_i.fill('phrase search: {0}'.format(name)))

def print_selected(entries, i):
	strn = str_from_list(False, entries, i, '', ' | ', '').strip()
	divider()
	print(tw_i.fill('selected: {0}'.format(strn)))
	
def print_list_or_return(entries):
	num = 1
	if len(entries) >= 1:
		cl_divider()
		for entry in entries:
			print(tw_i.fill('{0}. {1}'.format(str(num), entry[1])))
			num += 1
		divider()
		print(tw_i.fill('entries found: {0}'.format(len(entries))))
	elif len(entries) == 0: 
		cl_divider()
		print(tw.fill("nothing found ':' for options"))
	if len(entries) == 1: 
		return entries[0] #return what was found by narrowing down
		
def print_zettels_links_z_id(flag, titles, current_title):
	num = 1
	cl_divider()
	for title in titles:
		print(tw_i.fill('{0}. {1}'.format(str(num), title)))
		num += 1
	print()
	if flag == 'from': print(tw.fill('zettels linked by: {0} - {1}'.format(current_title, len(titles))))
	elif flag == 'to': print(tw.fill('zettels linking to: {0} - {1}'.format(current_title, len(titles))))

def print_picking_same_zettel():
	divider()
	print(tw.fill('''
selected the same zettel you are linking from, it will be omitted
'''.strip()))

#SEARCHING / MAKING TAGS
def print_detached_tag_rename():
	cl_divider()
	print(tw.fill('''
attempted to rename a detached tag, the tag shouldn't have existed
in the first place and will be deleted
'''.strip()))

def print_tag_search_stats(name):
	print(tw_i.fill('phrase search: {0}'.format(name)))
	
def print_tag_info(titles, listed_tag):
	cl_divider()
	print(tw_i.fill('selected tag: {0}'.format(listed_tag)))
	print(tw_i.fill('zettels under tag: {0}'.format(len(titles))))
	
def print_zettels_under_tag(titles, tag):
	num = 1
	cl_divider()
	for title in titles:
		print(tw_i.fill('{0}. {1}'.format(str(num), title)))
		num += 1
	print()
	print(tw_i.fill('zettels under tag: {0} - {1}'.format(tag[1], len(titles))))

#DB META
def print_db_meta(db_name):
	meta = read_meta_all(db_name)
	cl_divider()
	print(tw_i.fill('database name: {}'.format(meta[1])))
	print(tw_i.fill('created: {}'.format(meta[2])))
	print(tw_i.fill('total number of zettels: {}'.format(meta[3])))
	print(tw_i.fill('total number of links: {}'.format(meta[4])))
	divider()
	print(tw_i.fill('warnings:'))
	print(tw_i.fill('zettels without links: {}'.format(meta[5])))
	print(tw_i.fill('zettels that link to themselves: {}'.format(meta[6])))
	print(tw_i.fill('empty zettels: {}'.format(meta[7])))
	print(tw_i.fill('zettels without titles: {}'.format(meta[8])))

#GIT OPS
def print_git_current_head(): 
	divider() 
	print(tw_i.fill('Current head:'))
	os.system("git log --branches --oneline -n 1")

def print_git_status():
	cl_divider()
	os.system("git status")

def print_git_log(entries):
	cl_divider()
	os.system("git log --branches --oneline -n "+str(entries)); 
	
def print_git_push():
	cl_divider()
	os.system("git push --all")
	
def print_git_add_modified():
	cl_divider()
	print(tw_i.fill('New / modified files:'))
	os.system("git add . ")
	os.system("git status --short")
	
#▒▒▒▒▒▒▒▒▒▒▒▒ MENUS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_main_ops():
	cl_divider()
	print(tw_i.fill('(i) - show statistics'))
	print(tw_i.fill('(z) - find zettel to enter the database'))
	print(tw_i.fill('(t) - browse tags in the database'))
	print(tw_i.fill('(r) - review zettels for errors in links and content'))
	print(tw_i.fill('(n) - make a new zettel'))
	print(tw_i.fill('(init) - make a new database (name in script header)'))
	print(tw_i.fill('(temp) - generate a template .md zettel'))
	print(tw_i.fill('(test) - generate a batch of test zettels'))
	print(tw_i.fill('(import) - import .md zettels to the database'))
	print(tw_i.fill('(compile) - compile this .py into .pyc for safety'))
	print(tw_i.fill('(git) - git menu'))
	print(tw_i.fill('(q) - quit'))

def print_git_ops():
	cl_divider()
	print(tw_i.fill('() - current'))
	print(tw_i.fill('(l) - log'))
	print(tw_i.fill('(s) - status'))
	print(tw_i.fill('(c) - commit all'))
	print(tw_i.fill('(p) - push'))
	print(tw_i.fill('(r) - revert'))
	print(tw_i.fill('(ha) - hard reset'))
	print(tw_i.fill('(u) - launch "gitui" (must be installed)'))
	print_q()

#ZETTEL OPS MENUS
def print_search_zettel_ops():
	divider()
	print(tw_i.fill("'number' - select entry"))
	print(tw_i.fill("(t) - select tags for filter"))
	print(tw_i.fill("(ew) - edit search phrase"))
	print(tw_i.fill("(cw) - clear search phrase"))
	print(tw_i.fill("(ct) - clear search tags"))
	print(tw_i.fill('(n) - make a new zettel'))
	print_qc('q')
	print_qm()
	
def print_select_zettel_ops():
	divider()
	print(tw_i.fill("'number' - inspect entry"))
	print_qc('')
	print_qm()

def print_zettel_ops():
	divider()
	print_qc('')
	print(tw_i.fill('(lt) - linked to →'))
	print(tw_i.fill('(lb) - linked by ←'))
	print(tw_i.fill('(x) - zettel extra actions'))
	print(tw_i.fill('(e) - zettel edit options'))
	print_qm()
	
def print_zettel_ops_lim():
	divider()
	print_qc('')
	print_qm()

def print_zettel_edit_ops():
	divider()
	print(tw_i.fill('(n) - edit title (name)'))
	print(tw_i.fill('(b) - edit text body'))
	print(tw_i.fill('(l) - edit outgoing links'))
	print(tw_i.fill('(t) - edit tags'))
	print(tw_i.fill('(d) - delete zettel'))
	
def print_zettel_extra_ops():
	divider()
	print(tw_i.fill("(nlt) - follow n-times 'linked to' → →"))
	print(tw_i.fill("(nlb) - follow n-times 'linked by' ← ←"))
	print(tw_i.fill('(nal) - follow n-times all linked  ← →'))

#TAG OPS MENUS
def print_search_tag_edit():
	divider()
	print(tw_i.fill("'number' - select entry"))
	print(tw_i.fill("(ew) - edit search phrase"))
	print(tw_i.fill("(cw) - clear search phrase"))
	print(tw_i.fill('(n) - make a new tag'))
	print_qc('q')
	print_qm()
	
def print_search_tag_view():
	divider()
	print(tw_i.fill("'number' - select entry"))
	print(tw_i.fill("(ew) - edit search phrase"))
	print(tw_i.fill("(cw) - clear search phrase"))
	print_qc('q')
	print_qm()
	
def print_tag_ops():
	divider()
	print_qc('')
	print(tw_i.fill('(i) - inspect zettels under tag'))
	print(tw_i.fill('(e) - edit tag name (globally)'))
	print_qm()
	
def print_only_one_tag_in_list(entry): 
	cl_divider(); 
	print(tw.fill('there is only one entry in the list: {0}'.format(entry[1])))
	print(tw_i.fill('(p) - select it and proceed'))
	print(tw_i.fill('(n) - make a new tag'))
	print_qm()
	

#▒▒▒▒▒▒▒▒▒▒▒▒ STANDARD PROMPTS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def c_prompt(prompt): 
	divider(); 
	try: inp = input(prompt+" : ").rstrip()
	except KeyboardInterrupt: inp = ''
	return inp 
	
def s_prompt(prompt):
	divider(); 
	try: inp = input(prompt+" > ").rstrip()
	except KeyboardInterrupt: inp = ''
	return inp 
	
def p(): divider(); l=(text_width-10)//2; s="░"*l+" CONTINUE "+"░"*l; input(s)
def print_qc(ch): print(tw_i.fill("({0}) - return | confirm".format(ch)))
def print_q(): print(tw_i.fill('(q) - return'))
def print_qm(): print(tw_i.fill('(qm) - return to main menu | abort everything'))

#▒▒▒▒▒▒▒▒▒▒▒▒ CLEAR SCREEN AND DIVIDER ▒▒▒▒▒▒▒▒▒▒▒▒▒
def divider(): 
	d_line = '─' * text_width
	print(d_line)
def cl(): os.system('cls' if os.name == 'nt' else 'clear')
def cl_divider(): cl(); divider()

#▒▒▒▒▒▒▒▒▒▒▒▒ GIT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def git_info(): print_git_current_head()
def git_status(): print_git_status()
def git_log_f(): 
	entries = write_num_not_empty('int', 'commits to print')
	print_git_log(entries)
	
def git_launch_gitui(): os.system('gitui')
def git_push(): print_git_push()

def git_commit_f():
	print_git_add_modified(); print_git_current_head();p()
	comment = '# Enter the new commit name below\n'
	commit_name = write_not_empty(comment, flag=None, allow_exit=True)
	if commit_name =='': return
	inp = c_prompt("really? ('yes' to proceed)")
	if inp == "yes": os.system("git commit -m "+ '\"'+commit_name+'\"')
	
def git_revert_f():
	git_log_f(); p()
	comment = '# Enter the commit name to revert to below\n'
	commit_name = write_not_empty(comment, flag=None, allow_exit=True)
	if commit_name =='': return
	os.system("git revert "+ '\"'+commit_name+'\"')
	
def git_reset_hard_f():
	git_log_f(); p()
	comment = '# Enter the commit name to RESET to below\n'
	commit_name = write_not_empty(comment, flag=None, allow_exit=True)
	if commit_name =='': return
	inp = c_prompt("really? ('yes' to proceed)")
	if inp == "yes": os.system("git reset --hard "+ '\"'+commit_name+'\"')

#▒▒▒▒▒▒▒▒▒▒▒▒ FORMAT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def list_by_tag(tag_id):
	titles = []; tagged_zettels = []
	listed_tag = read_taglist_id(tag_id)[1]
	tags = read_tags_tag(listed_tag)
	for tag in tags:
		z_id = tag[1]
		zettel = read_main_id(z_id)
		z_title = zettel[1]
		tagged_zettels.append(zettel)
		titles.append(z_title)
	return (tagged_zettels, titles, listed_tag,)
	
def list_by_links_z_id_from(z_id):
	titles = []; linked_zettels = []
	links = read_links_z_id_from(z_id)
	for link in links:
		z_id_to = link[2]
		zettel = read_main_id(z_id_to)
		z_title = zettel[1]
		linked_zettels.append(zettel)
		titles.append(z_title)
	return (linked_zettels, titles,)
	
def list_by_links_z_id_to(z_id):
	titles = []; linked_zettels = []
	links = read_links_z_id_to(z_id)
	for link in links:
		z_id_from = link[1]
		zettel = read_main_id(z_id_from)
		z_title = zettel[1]
		linked_zettels.append(zettel)
		titles.append(z_title)
	return (linked_zettels, titles,)

def str_from_list(sort_flag, init, i, li, lm, le):
	def process(fin, li, lm, le):
		strn = ''; pos = 0
		if len(fin) == 1:
			strn += li + fin[0] +le
		elif len(fin) == 2:
			strn += li + fin[0] + lm + fin[1] +le
		else:
			for entry in fin: 
				if pos == 0: strn += li + str(entry) + lm
				elif not pos == len(fin)-1: strn += str(entry)+lm
				else: strn += str(entry)+le
				pos += 1
		return strn
	fin = []; 
	if i:
		for entry in init: fin.append(entry[i])
	else: 
		for entry in init: fin.append(entry)
	if sort_flag: fin.sort()
	strn = process(fin, li, lm, le)
	return strn

#▒▒▒▒▒▒▒▒▒▒▒▒ DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def import_zettels():
	#str?
	import_to_db();
	
def delete_from_db(query, exec_line, db_path):
	conn = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if query: 
					c.execute(exec_line, (query,))
				else: 
					c.execute(exec_line)
			except Error as e: print(e); p(); main_menu()
			conn.commit(); conn.close();
	
def query_db(query, exec_line, db_path):
	found = []; conn = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if query: 
					c.execute(exec_line, (query,))
				else: 
					c.execute(exec_line)
				found = c.fetchall()
			except Error as e: print(e); p(); main_menu()
			conn.close(); return found
			
def query_tags(tag, db_path): #for AND condition filtering
	found = []; conn = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if tag: 
					c.execute(select_tags_tag, (tag,))
				else: 
					return found
				found = c.fetchall()
			except Error as e: print(e); p(); main_menu()
			conn.close(); return found
			
def add_to_db(entry, exec_line, db_path):
	conn = None; id = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if len(entry) == 1: c.execute(exec_line, (entry[0],))
				elif len(entry) == 2: c.execute(exec_line, (entry[0], entry[1],))
				elif len(entry) == 3: c.execute(exec_line, (entry[0], entry[1], entry[2],))
				elif len(entry) == 8: c.execute(exec_line, (entry[0], entry[1], entry[2],
					entry[3], entry[4], entry[5], entry[6], entry[7],))
				else: #an exception
					print('Attempted to write', len(entry), 'fields, which is not supported')
					print('The SQLite command is:', exec_line)
					quit()
			except Error as e: print(e); p(); main_menu()
			conn.commit()
			id = c.lastrowid
			conn.close();
			return id
			
def incr_add_to_db(entry_list, exec_line, db_path):
	conn = None; id = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				for entry in entry_list:
					if len(entry) == 1: c.execute(exec_line, (entry[0],))
					elif len(entry) == 2: c.execute(exec_line, (entry[0], entry[1],))
					elif len(entry) == 3: c.execute(exec_line, (entry[0], entry[1], entry[2],))
					else:  #an exception
						print('Attempted to write', len(entry), 'fields, which is not supported')
						print('The SQLite command is:', exec_line)
						quit()
			except Error as e: print(e); p(); main_menu()
			conn.commit()
			id = c.lastrowid
			conn.close();
			return id

def import_to_db():
	print_importing_warn(); p()
	comment = '# Enter the name of the local folder \n# which contains .md files below\n'
	inp = write_not_empty(comment, 'prompt', allow_exit=False)
	if not os.path.isdir(inp):
		print_importing_failed(); return #failed
	dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
	dt_str_file = time.strftime("%d%b%Y%H%M%S", time.localtime())
	db_name_imported = os.path.join('imported_' + inp + '_' + dt_str_file + '.db')
	#db_name_imported = current_db_path
	conn = None
	try: conn = sqlite3.connect(db_name_imported)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				time_start = time.time()
				c = conn.cursor()
				#create tables
				c.execute(create_meta_table); c.execute(create_main_table)
				c.execute(create_links_table); 
				c.execute(create_no_links_table); c.execute(create_self_links_table)
				c.execute(create_tags_table); c.execute(create_no_bodies_table)
				c.execute(create_no_titles_table); c.execute(create_taglist_table);
				#populate tables
				links = []; invalid_links = []; dupe_links = []; written_links = []
				#main table
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name: continue #skip it
						full_path = os.path.join(root, name)
						parsed = parse_zettel_from_file(full_path)
						z_path = name
						z_title = parsed['title']
						z_body = parsed['body']
						tags = parsed['tags']
						#first write main table
						c.execute(insert_main, (z_title, z_path, z_body))
						#get the current zettel id
						c.execute(select_main_z_path, (z_path,))
						current_zettel_id = c.fetchall()[0][0]
						#store metadata
						for tag in tags:
							c.execute(insert_tags, (current_zettel_id, tag,))
							c.execute(insert_taglist, (tag,))
				#links must be done only once main tabe is populated
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name: continue #skip it
						full_path = os.path.join(root, name)
						parsed = parse_zettel_from_file(full_path)
						z_path = name
						z_title = parsed['title']; links = parsed['links']
						#get the current zettel id
						c.execute(select_main_z_path, (z_path,))
						current_zettel_id = c.fetchall()[0][0]
						#see if links point out to existing nodes
						for link in links:
							link_path = link[1]; link_desc = link[0]
							c.execute(select_main_z_path, (link_path,))
							found_zettel = c.fetchall()
							if found_zettel:
								valid_zettel_id = found_zettel[0][0]
								if valid_zettel_id != current_zettel_id: #make sure it doesn't point to itself
									if not (current_zettel_id, valid_zettel_id,) in written_links: #no dupes allowed
										c.execute(insert_links, (current_zettel_id, valid_zettel_id, link_desc));
										written_links.append((current_zettel_id, valid_zettel_id,))
									else: dupe_links.append((current_zettel_id, z_title, z_path, link_path, link_desc))
							else: invalid_links.append((current_zettel_id, z_title, z_path, link_path,))
				conn.commit()
				time_end = time.time()
				t = time_end - time_start
				print_importing_succeeded(database_name, t)
				if invalid_links: print_invalid_links(invalid_links); p()
				if dupe_links: print_dupe_links(dupe_links); p()
			except Error as e: print(e); p(); main_menu()
			conn.close();
			
def init_new_db():
	print_init_new_db(); p()
	comment = '# Enter the name of a new database below\n'
	database_name = write_not_empty(comment, 'prompt', allow_exit=False)
	new_db_path = os.path.join(os.getcwd(), database_name + '.db')
	if os.path.isfile(new_db_path): print_db_exists(); p(); return
	dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
	conn = None
	try: conn = sqlite3.connect(new_db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				#create tables
				c.execute(create_meta_table); c.execute(create_main_table)
				c.execute(create_links_table); 
				c.execute(create_no_links_table); c.execute(create_self_links_table)
				c.execute(create_tags_table); c.execute(create_no_bodies_table)
				c.execute(create_no_titles_table); c.execute(create_taglist_table);
				#write meta
				c.execute(insert_meta, (database_name, dt_str, 0, 0, 0, 0, 0, 0,))
				conn.commit()
			except Error as e: print(e); p(); main_menu()
			conn.close()
			print_db_meta(new_db_path)
			p()

#▒▒▒▒▒▒▒▒▒▒▒▒ FILE & TEST OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def compile_myself():
	py_compile.compile(
		file='zettel-pycli.py', 
		cfile='zettel-pycli.pyc',
		optimize=2,)
	p()
	
def gen_template():
	f = open(zettel_template_name, "w")
	f.write(zettel_template)
	f.close(); p()
	
def make_test_zettels():
	if make_test_batch(): print_made_tests()
	
def make_test_batch():
	lorem_raw = '''
Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
In sit amet congue sem. Proin a ligula aliquam, ullamcorper 
augue quis, blandit leo. Nulla egestas feugiat urna, quis 
sodales est egestas in. Aliquam blandit hendrerit porta. 
Cras in molestie erat, sit amet fermentum velit. Phasellus ac 
ex non lacus placerat euismod vel fringilla tellus. Donec 
tempus tortor vestibulum sapien sollicitudin luctus. Nam 
in est ac urna luctus maximus.
Donec eu lorem a turpis tempus mollis. Aenean molestie porta 
massa sit amet luctus. Nam volutpat maximus sem, et accumsan 
diam pulvinar eget. Sed tempus rhoncus nunc vitae ornare. 
Vestibulum maximus massa quis neque auctor rutrum. 
Suspendisse feugiat, leo eget aliquet facilisis, est sem tincidunt 
massa, malesuada pretium nibh nibh at turpis. Nam vehicula 
est ac tellus facilisis ultrices.
Morbi non eros gravida, rutrum sapien at, tincidunt velit.
Cras consectetur magna laoreet tellus convallis, a sollicitudin lorem 
ornare. Proin nisi velit, mollis ac rutrum mattis, pretium nec augue. 
Integer vulputate vulputate ipsum pellentesque blandit. Pellentesque 
a purus magna. Phasellus pulvinar orci est, eget semper sapien 
blandit vitae. Pellentesque viverra sem quis turpis aliquet, quis venenatis 
justo ultricies. Ut rutrum, ligula in viverra pellentesque, metus velit 
sollicitudin sem, quis accumsan lacus turpis a mi. Nulla facilisi. 
Vestibulum vehicula vulputate porta. Proin suscipit diam eu enim 
dapibus, et volutpat erat consequat. '''
	lorem_init = lorem_raw.split(' '); lorem_raw = []
	for word in lorem_init:
		lorem_raw.append(word.strip())
	
	print_test_warn()
	inp_num = write_num_not_empty('int', 'how many zettels to make?')
	inp_links = write_num_not_empty('int', 'how many links per zettel')
	inp_corr = write_num_not_empty('float', 'amount of correct zettels (0.0..1.0)')
	#perfect zettels
	for i in range(inp_num):
		lorem_full = ' '.join(random.sample(lorem_raw, len(lorem_raw)))
		t = random.randrange(35)
		r = random.randrange(len(lorem_full)-t)
		lorem = tw.fill(lorem_full[:r])
		title = tw.fill(lorem_full[r:r+t])
		frnd = random.random(); frnd2 = random.random(); frnd3 = random.random() 
		if frnd < 0.1: tags = 'performance, zettel, test, tags, python'
		elif frnd < 0.2 and frnd >= 0.11: tags = 'test, zettel'
		elif frnd < 0.3 and frnd >= 0.21: tags = 'tags, test'
		elif frnd < 0.4 and frnd >= 0.31: tags = 'test, tags'
		elif frnd < 0.5 and frnd >= 0.41: tags = 'performance, zettel'
		elif frnd < 0.6 and frnd >= 0.51: tags = 'test, python'
		elif frnd < 0.7 and frnd >= 0.61: tags = 'performance, test'
		elif frnd < 0.8 and frnd >= 0.71: tags = 'performance, python'
		elif frnd < 0.9 and frnd >= 0.81: tags = 'performance, tags'
		elif frnd < 1.0 and frnd >= 0.91: tags = 'performance, test'
		else: tags = ''
		
		if frnd <= inp_corr:
			links = ''
			try: #generate links, avoiding self-linking
				for j in range(inp_links):
					rnd = random.randrange(inp_num)
					if rnd == i: rnd += 1
					if rnd == inp_num: rnd -= 2
					links += '['+title+' links to: ' +str(rnd)+'.md because...]('+str(rnd)+'.md)  \n'
			except ValueError: pass
			zettel_template_test = marker_title + '  \n' + title \
			+ '  \n\n' + marker_body + '  \n' + lorem + '  \n\n' + marker_tags + '  \n' \
			+ tags + '  \n\n' + marker_links + '  \n' + links
		else: #bad zettels
			links = ''
			try: #make some wrong links
				if frnd2 < 0.25:
					for j in range(inp_links):
						rnd = random.randrange(inp_num)
						links += '['+title+' links to: ' +str(rnd)+'.md because...]('+str(rnd)+'.md)  \n'
				elif frnd2 < 0.5 and frnd2 >= 0.25: links += '[some](broken link)'
				elif frnd2 < 0.75 and frnd2 >= 0.5: links += '[Self link '+str(i+1)+']('+str(i+1)+'.md)\n'
				else: pass
			except ValueError: pass
			
			if frnd3 < 0.33: #make some wrong zettels
				zettel_template_test = marker_title + '  \n' \
				+ '  \n\n' + marker_body + '  \n' + lorem + '  \n\n' + marker_tags + '  \n' \
				+ tags + '  \n\n' + marker_links + '  \n' + links
			elif frnd3 < 0.66 and frnd3 >= 0.33:
				zettel_template_test = marker_title + '  \n' + title \
				+ '  \n\n' + marker_body + '  \n\n' + marker_tags + '  \n' \
				+ tags + '  \n\n' + marker_links + '  \n' + links
			elif frnd3 <= 1.0 and frnd3 >= 0.66:
				zettel_template_test = marker_title + '  \n' \
				+ '  \n\n' + marker_body + '  \n\n' + marker_tags + '  \n' \
				+ tags + '  \n\n' + marker_links + '  \n' + links
		if not os.path.exists(path): os.mkdir(path)
		f = open(path + "/" + str(i) + '.md', "w")
		f.write(zettel_template_test); f.close()
	return True #succeeded
	
#▒▒▒▒▒▒▒▒▒▒▒▒ PARSING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def find_md_links(md):
	INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
	links = list(INLINE_LINK_RE.findall(md))
	return links

def find_comma_separated(md):
	COMMA_SEP_CONT = re.compile(r'(.+?)(?:,\s*|$)')
	text = list(COMMA_SEP_CONT.findall(md))
	return text
	
def parse_off_comments(text):
	out = ''
	for line in text.splitlines(True):
		if line.lstrip().startswith('#'): continue
		else: out += line
	return out
	
def parse_zettel_from_file(z_path):
	data = {'title' : '', 'body' : '', 'tags' : [], 'links' : [], }
	f = open(z_path, 'r')
	#a switch flag to read links in tge end of the file
	reading_title = False
	reading_body = False
	reading_links = False
	reading_tags = False
	#parse keywords
	for line in f:
		if marker_body in line:
			reading_title = False
			reading_body = True
			reading_tags = False
			reading_links = False
			continue
		if marker_title in line:
			reading_title = True
			reading_body = False
			reading_tags = False
			reading_links = False
			continue
		if marker_tags in line:
			reading_title = False
			reading_body = False
			reading_tags = True
			reading_links = False
			continue
		if marker_links in line:
			reading_title = False
			reading_body = False
			reading_tags = False
			reading_links = True
			continue
		if reading_title: data['title'] += line.strip()
		if reading_body: data['body'] += line.strip()
		if reading_tags: data['tags'] += find_comma_separated(line)
		if reading_links: data['links'] += find_md_links(line)
	return data


#▒▒▒▒▒▒▒▒▒▒▒▒ START ▒▒▒▒▒▒▒▒▒▒▒▒▒
main_menu()
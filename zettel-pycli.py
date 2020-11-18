#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
kasten_name = "my_vault"


#▒▒▒▒▒▒▒▒▒▒▒▒ CREDITS & LICENCE ▒▒▒▒▒▒▒▒▒▒▒▒▒
# https://writingcooperative.com/zettelkasten-how-one-german-
#	scholar-was-so-freakishly-productive-997e4e0ca125 - idea
# https://www.sqlitetutorial.net/sqlite-python/ - db oos
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


#▒▒▒▒▒▒▒▒▒▒▒▒ SCRIPT BODY ▒▒▒▒▒▒▒▒▒▒▒▒▒
#Init stuff
import os, fnmatch, shutil, pathlib, sqlite3, time, re
from sqlite3 import Error

path = os.path.join(os.getcwd(), kasten_name)
db_path = os.path.join(os.getcwd(), kasten_name + '_index.db')
pathlib.Path(path).mkdir(parents=True, exist_ok=True)

#SQL schemas
create_main_table = '''
	CREATE TABLE IF NOT EXISTS main (
		id integer PRIMARY KEY,
		z_title text NOT NULL,
		z_path text NOT NULL
	); '''

create_link_table = '''
	CREATE TABLE IF NOT EXISTS links (
		id integer PRIMARY KEY,
		l_from integer NOT NULL,
		l_to integer NOT NULL
	); '''

insert_main = '''
	INSERT INTO main (
		z_title,
		z_path
	)
	VALUES(
		?, ?
	) '''

insert_links = '''
	INSERT INTO links (
		l_from,
		l_to
	)
	VALUES(
		?, ?
	) '''
	

#Just fancy stuff
banner_git	  = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒GIT MENU▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_log	  = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒LOG▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_commit   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒COMMITTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_revert   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒REVERTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_hreset   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒HARD RESETTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_zettel	 = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ZETTEL MENU▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
divider = '-------------------------------------------------------'

#▒▒▒▒▒▒▒▒▒▒▒▒ GIT MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def git_menu():

	git_log = "git log --branches --oneline -n 20"
	git_log_1 = "git log --branches --oneline -n 1"
	git_status = "git status"
	git_add = "git add . && git status --short"
	git_push = "git push --all"
	
	def print_git_ops():
		print('')
		print(banner_git)
		print('() - current')
		print('(l) - log')
		print('(s) - status')
		print('')
		print('(a) - add')
		print('(c) - commit')
		print('(p) - push')
		print('')
		print('(r) - revert')
		print('(ha) - hard reset')
		print(banner_git)
		print('')
		print('(u) - launch "gitui"')
		print('(q) - quit to main')
	
	def git_log_f():
		print(banner_log)
		os.system(git_log)
		print(banner_log)
	
	def git_commit_f():
		print(banner_commit)
		print('Files added:')
		os.system(git_add)
		print('Current head:')
		os.system(git_log_1)
		print(banner_commit)
		commit_name = input("New commit name (' ' to abort) » ").strip()
		if commit_name =="":
			return
		inp = input("Really commit? » ").strip()
		if inp == "yes":
			git_commit = "git commit -m "+commit_name
			os.system(git_commit)
		
	def git_revert_f():
		print(banner_revert)
		print('Commits:')
		os.system(git_log)
		print(banner_revert)
		commit_name = input("Revert to commit name (' ' to abort) » ").strip()
		if commit_name =="":
			return
		git_revert = "git revert "+commit_name
		os.system(git_revert)
		
	def git_reset_hard_f():
		print(banner_hreset)
		print('Commits:')
		os.system(git_log)
		print(banner_hreset)
		commit_name = input("Reset to commit name (' ' to abort) » ").strip()
		if commit_name =="":
			return
		inp = input("Really? » ").strip()
		if inp == "yes":
			git_reset_hard = "git reset --hard "+commit_name
			os.system(git_reset_hard)
	
	#Begin
	print_git_ops()
	while True:
		print('')
		inp = input("GIT MENU ('?' for commands) » ").strip()
		print('')
				
		if inp == "l":
			git_log_f()
		elif inp == "":
			print('Current head:')
			os.system(git_log_1)
		elif inp == "s":
			os.system(git_status)
		elif inp == "a":
			os.system(git_add)
		elif inp == "c":
			git_commit_f()
		elif inp == "p":
			os.system(git_push)
		elif inp == "r":
			git_revert_f()
		elif inp == "ha":
			git_reset_hard_f()
		elif inp == "?":
			print_git_ops()
		elif inp == "u":
			os.system('gitui')
		elif inp == "q":
			break
			
#▒▒▒▒▒▒▒▒▒▒▒▒ ZETTEL MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def main_menu():
	
	def print_main_ops():
		print('')
		print(banner_zettel)
		print('() - update the index and show brief statistics')
		print('(tree) - use "tree" command to show files')
		print(banner_zettel)
		print('')
		print('(t) - git menu')
		print('(q) - quit')
		
	def find_md_links(md):
		INLINE_LINK_RE = re.compile(r'\(([^)]+)\)')
		links = list(INLINE_LINK_RE.findall(md))
		return links
	
	def find_comma_separated(md):
		COMMA_SEP_CONT = re.compile(r'(.+?)(?:,\s*|$)')
		text = list(COMMA_SEP_CONT.findall(md))
		return text
		
	def parse_zettel(z_path):
		#expected parsed data
		data = {
			'title' : '',
			'tags' : [],
			'links' : [],
		}
		
		# open the file and read through it line by line
		f = open(z_path, 'r')
		
		#a switch flag to read links in tge end of the file
		reading_title = False
		reading_links = False
		reading_tags = False
		
		#parse keywords
		for line in f:
			
			if "[BODY]" in line:
				reading_title = False
				reading_tags = False
				reading_links = False
				continue
		
			if "[TITLE]" in line:
				reading_title = True
				reading_tags = False
				reading_links = False
				continue
			
			if "[TAGS]" in line:
				reading_title = False
				reading_tags = True
				reading_links = False
				continue
		
			if "[ZETTEL LINKS]" in line:
				reading_title = False
				reading_tags = False
				reading_links = True
				continue
			
			if reading_title:
				data['title'] += line.strip()
				
			if reading_tags:
				data['tags'] += find_comma_separated(line)
				
			if reading_links:
				data['links'] += find_md_links(line)
					
		print('Title: ', data['title'])
		print('Tags: ', data['tags'])
		print('Links: ', data['links'])
				
		return data
			
		
	def update_db():
		
		#remove existing db
		os.remove(db_path)
		
		#create new db
		conn = None
		try:
			conn = sqlite3.connect(db_path)
		except Error as e:
			print(e)
		finally:
			if conn:
				try:
					c = conn.cursor()
					
					#create tables
					c.execute(create_main_table)
					c.execute(create_link_table)
					
					#populate tables
					time_start = time.time()
					for root, dirs, files in os.walk(path):
						for name in files:
							z_path = os.path.join(root, name)
							z_title = parse_zettel(z_path)['title']
							c.execute(insert_main, (z_title, z_path,))
					
					for i in range(0, 10000):
						l_from = i
						l_to = i+53
						c.execute(insert_links, (l_from, l_to,))
					
					conn.commit()
					time_end = time.time()
					print('database rebuilt in: ', time_end - time_start)
				
				except Error as e:
					print(e)
				conn.close()
	
	def get_entry_num(pattern):
		num = 0
		for root, dirs, files in os.walk(path):
			for name in files:
				if fnmatch.fnmatch(name, pattern):
					num += 1
		return num
	
	#Higher-level functions
	def statistics():
		entries_num = get_entry_num('*.md')
		print(divider)
		print('current number of zettel .md files is: ' + str(entries_num))
		print(divider)
		
	def tree():
		os.system('tree'+' '+path)
		print(divider)
		print('tree rendred')
		print(divider)
	
	#while True:
	print_main_ops()
	
	while True:
		print('')
		inp = input("MAIN MENU ('?' for commands) » ").strip()
		print('')
				
		if inp == "":
			os.system('clear')
			update_db()
			statistics()
		if inp == "tree":
			os.system('clear')
			tree()
		elif inp == "t":
			os.system('clear')
			git_menu()
		elif inp == "?":
			print_main_ops()
		elif inp == "q":
				quit()

#Start
os.system('clear')
while True:
	main_menu()

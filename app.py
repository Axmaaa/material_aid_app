#!/usr/bin/python3

import sys
import sqlite3 as db
import functools

from PyQt5.QtWidgets import (
	QApplication, QLabel, QListWidgetItem, QFileDialog, QWidget, QDialog, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import (QFont, QBrush, QColor)
from PyQt5.QtCore import (Qt, QSize)
from PyQt5 import uic
from PyQt5 import QtCore

DB_PATH = 'my_db.s3db'
TABLENAME = 'students'
TAXES = 0.13

FormUI, Form = uic.loadUiType('mataid.ui')

class my_widget(Form):
	
	def __init__(self, parent=None):
		super().__init__()
		self.ui = ui = FormUI()
		ui.setupUi(self)
		self.setWindowTitle("Material aid")
		self.ui.button_show.clicked.connect(self.__show)
		self.ui.button_appoint_aid.clicked.connect(self.__appoint_aid)
		self.ui.aid_summ.setMaximum(100000.00)
		self.ui.aid_summ.setMinimum(-100000.00)
		self.max_persons1 = int(self.ui.persons_1.text())
		self.max_persons2 = int(self.ui.persons_2.text())
		self.students_selection_buttons = []
		self.dbc = db.connect(DB_PATH)


	def __del__(self):
		self.ui = None
		if self.dbc is not None:
			self.dbc.close ()


	def __params_to_where(self):
		group_number = self.ui.group_number.text().strip()
		department = self.ui.department.text().strip()
		course_number = self.ui.course_number.text().strip()
		school_number = self.ui.school_number.text().strip()
		names = self.ui.full_name.text().strip().split(' ')
		last_name, first_name, second_name = [names[i] if i < len(names) else '' for i in range(3)]

		query_parameters = [
			['group_num', group_number], 
			['department', department],
			['course_num', course_number],
			['school_num', school_number],
			['lastname', last_name],
			['first_name', first_name],
			['second_name', second_name]]

		if functools.reduce(lambda a, b: a + b, [param for _, param in query_parameters]) != '':
			text = ' WHERE ' + ' AND '.join([column_name + ' = ?' for column_name, value in query_parameters if value != ''])
			params = tuple([value for _, value in query_parameters if value != ''])
		else:
			text = ''
			params = None
		return text, params


	def __show_query_result_table(self, students_table):
		table = self.ui.query_result_table
		column_count = len(students_table[0]) + 1
		row_count = len(students_table) 
		table.setColumnCount(column_count)
		table.setRowCount(row_count)
		self.students_selection_buttons = []
		for i in range(row_count):
			for j in range(column_count):
				table_item = QTableWidgetItem()
				table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
				if i == 0 and j == 0:
					table_item.setText('Select')
					table.setItem(i, j, table_item)
				elif i != 0 and j == 0:
					#table.setItem(i, j, table_item)
					check_box = QCheckBox()
					self.students_selection_buttons.append(check_box)
					table.setCellWidget(i, j, check_box)
				else:
					if j > 3:
						table_item.setTextAlignment(3)
					font = QFont("Times", 14)
					if i == 0:
						font.setBold(True)
					table_item.setFont(font)
					table_item.setText(students_table[i][j - 1])
					table.setItem(i, j, table_item)
		header = table.horizontalHeader()
		header.setSectionResizeMode(QHeaderView.ResizeToContents)
	

	def __show_message_in_table(self, message, rgb):
		table = self.ui.query_result_table
		column_count = 1
		row_count = 1
		table.setColumnCount(column_count)
		table.setRowCount(row_count)
		message_item = QTableWidgetItem(message)
		r, g, b = rgb
		color = QColor(r, g, b)
		brush = QBrush(color)
		message_item.setForeground(brush)
		table.setItem(0, 0, message_item)
		table.item(0, 0).setFlags(message_item.flags() & ~Qt.ItemIsEditable)
		header = table.horizontalHeader()
		header.setSectionResizeMode(QHeaderView.ResizeToContents)


	def __show(self):
		# Initial query
		query_text = 'SELECT * FROM ' + TABLENAME
		# Query expansion
		where_text, params = self.__params_to_where()
		query_text += where_text + ' ORDER BY lastname ASC'
		if self.ui.persons_1.isChecked():
			query_text += f' LIMIT {self.max_persons1}'
		elif self.ui.persons_2.isChecked():
			query_text += f' LIMIT {self.max_persons2}'

		# Try to execute query
		try:
			cur = self.dbc.cursor()
			cur.execute(query_text) if params == None else cur.execute(query_text, params)
			self.dbc.commit()
			result = cur.fetchall()
			max_persons = 100
			if (len(result) > max_persons):
				if self.__ask_dialog('Warning', 'Too many students are in query! Please, select, how many students you want to show.', '100', 'All') == 'left':
					result = result[:max_persons]
			error = None
		except Exception as exc:
			result = None
			error = str(exc)
		# Display result or error
		if error is None:
			if not result and cur.description is not None:
				self.__show_message_in_table('No students', (0, 255, 0))
			elif cur.description is not None:
				students = [[]]
				columns_to_make_decimals = ['current_full_sum', 'tax_sum', 'pay_sum', 'requested_sum']
				indices_to_make_decimals = [i for i, column in enumerate(cur.description) if column[0] in columns_to_make_decimals]
				for column_name, *_ in cur.description:
					students[0].append(column_name)
				for row in result:
					students.append([str(cell) if i not in indices_to_make_decimals else '%3.2f' % (float(cell) / 100) for i, cell in enumerate(row)])
				self.__show_query_result_table(students)
			else:
				return

		else:
			self.__show_message_in_table(error, (255, 0, 0))
		cur.close()


	def __appoint_aid(self):
		# Getting summ of material aid
		aid_summ = int(self.ui.aid_summ.text().replace(',', ''))
		# Getting students
		table = self.ui.query_result_table
		students = [tuple([table.item(i + 1, c).text() for c in [1, 2, 3, 4]]) for i in range(table.rowCount() - 1) if self.students_selection_buttons[i].isChecked()]
		# Making queries
		query_text = 'UPDATE ' + TABLENAME + ' SET current_full_sum = current_full_sum + ' + str(aid_summ) + ', tax_sum = tax_sum + ' + str(int(aid_summ * TAXES)) + ', pay_sum = pay_sum + ' + str(aid_summ - int(aid_summ * TAXES)) + ' WHERE lastname = ? AND first_name = ? AND second_name = ? AND group_num = ?'
		try:
			cur = self.dbc.cursor()
			cur.executemany(query_text, students)
			self.dbc.commit()
			result = cur.fetchall()
			error = None
		except Exception as exc:
			result = None
			error = str(exc)
			self.__show_message_in_table(error, (255, 0, 0))


	def __ask_dialog(self, window_title, dialog_text, left_button_text, right_button_text):
		dialog = QDialog()
		DialogFormUI, _ = uic.loadUiType('dialog.ui')
		dialog.ui = DialogFormUI()
		dialog.ui.setupUi(dialog)
		dialog.setWindowTitle(window_title)
		dialog.ui.text_field.setText(dialog_text)
		dialog.ui.left_button.setText(left_button_text)
		dialog.ui.right_button.setText(right_button_text)
		dialog.ui.left_button.clicked.connect(dialog.reject)
		dialog.ui.right_button.clicked.connect(dialog.accept)
		if dialog.exec() == 0:
			return 'left'
		return 'right'


def main():
	app = QApplication(sys.argv)
	wid = my_widget()
	wid.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()

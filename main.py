import sys
import os
import sqlite3
import time
import random as rnd
from PyQt5 import uic
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QInputDialog, QLineEdit,\
    QTableWidgetItem
from PyQt5.Qt import QTimer


# TODO 1) отображение времени таймера 2) борда с результатами 3) иконка мута

class ScoreBoard(QMainWindow):
    def __init__(self):
        super(ScoreBoard, self).__init__()
        uic.loadUi('scoreui.ui', self)
        self.conn = sqlite3.connect('music_db.db')
        self.load_base()
        self.btn_delall.clicked.connect(self.deleteallscore)

    def load_base(self):
        query = '''SELECT * FROM Scoreboard'''
        res = self.conn.cursor().execute(query).fetchall()
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(["Номер игры", "Результат", "Имя игрока"])
        self.tableWidget.setRowCount(0)
        for i in range(3):
            self.tableWidget.setColumnWidth(i, 130)
        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))

    def deleteallscore(self):
        answ = QMessageBox.question(
            self, '', f"Точно очистить всю таблицу?",
            QMessageBox.Yes, QMessageBox.No)
        if answ == QMessageBox.Yes:
            query = '''DELETE FROM Scoreboard'''
            self.conn.cursor().execute(query)
            self.conn.commit()
            self.load_base()

    def closeEvent(self, event):
        self.conn.close()


class Guess(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('QTUI.ui', self)
        self.setWindowTitle('Игра «Угадай песню»')
        self.conn = sqlite3.connect('music_db.db')
        self.state_game = False
        self.played = []
        self.used = set()
        self.score = 0
        self.corr_answ = {'', ''}
        self.load_base.clicked.connect(self.load_own_musicdb)
        self.player = QMediaPlayer()
        self.timer = QTimer()
        self.selected_level = None
        self.answ_btn.clicked.connect(self.check_answ)
        self.easy_lvl_btn.clicked.connect(self.time_for_lvl)
        self.med_lvl_btn.clicked.connect(self.time_for_lvl)
        self.hard_lvl_btn.clicked.connect(self.time_for_lvl)
        self.load_own_sg.clicked.connect(self.load_own_song)
        self.start_btn.clicked.connect(self.start_game)
        self.stop_btn.clicked.connect(self.stop_game)
        self.volume_state.setValue(50)
        self.volume_state.valueChanged[int].connect(self.player.setVolume)
        self.btn_scorebrd.clicked.connect(self.show_scoreboard)

    def start_game(self):
        print('start')
        self.state_game = True
        if self.selected_level:
            self.able_btn(False, 'Игра началась, слушайте и пишите ответ в ввод ниже!')
            song_name, art_id, path_to_song = self.get_info_rnd_song()
            q = f'''SELECT Artist FROM Artist WHERE id={art_id}'''
            artist = sqlite3.connect('music_db.db').cursor().execute(q).fetchall()[0][0]
            set_name = set(song_name.lower().split())
            self.corr_answ = {artist.lower()} | set_name
            file = QUrl.fromLocalFile(path_to_song)
            cont = QMediaContent(file)
            self.player.setMedia(cont)
            self.player.play()
            self.timer.start()
            self.timer.timeout.connect(self.time_to_answ)
        else:
            self.verdict.setText('Не выбран уровень!')

    def stop_game(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.stop()
        self.timer.stop()
        self.able_btn(True, 'Игра прервана')
        if self.score:
            valid = QMessageBox.question(
                self, '', f"Сохранить реультат score: {self.score}",
                QMessageBox.Yes, QMessageBox.No)
            if valid == QMessageBox.Yes:
                valid_name = QMessageBox.question(
                    self, '', f"Хотите ли вы добавить имя к результату?",
                    QMessageBox.Yes, QMessageBox.No)
                if valid_name == QMessageBox.Yes:
                    playername = QInputDialog.getText(self, "Добавление имени к результату", "Введите имя игрока:",
                                                      QLineEdit.Normal)[0]
                    self.load_score(playername)
                else:
                    self.load_score()
        self.succs_sg.display(0)
        self.score = 0
        self.state_game = False

    def load_score(self, playername='NOT STATED'):
        self.conn.cursor().execute(f'''INSERT INTO Scoreboard(score, name) VALUES({self.score}, "{playername}")''')
        self.conn.commit()
        print('loaded')

    def show_scoreboard(self):
        self.score_brd = ScoreBoard()
        self.score_brd.show()

    def time_to_answ(self):
        self.player.stop()
        self.verdict.setText('У вас есть 7 сек для ответа')
        self.timer.setInterval(7000)
        self.timer.start()
        self.timer.timeout.connect(self.check_answ)

    def check_answ(self):
        if self.state_game:
            answer_text = set([e.lower() for e in self.answ_line.text().split()])
            print(answer_text, self.corr_answ)
            self.timer.stop()
            res = True if len(self.corr_answ & answer_text) >= len(self.corr_answ) // 2 else False
            if res:
                self.score += 1
                self.succs_sg.display(str(self.score))
                self.answ_line.setText('')
                self.start_game()
            else:
                self.answ_line.setText('')
                self.stop_game()
                self.selected_level = None
                self.sel_lvl.setText('Вы проиграли')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and self.state_game:
            self.check_answ()
            self.timer.stop()

    def time_for_lvl(self):
        lvl = self.sender().text()
        self.sel_lvl.setText(f'Выбранный уровень: {lvl}')
        self.selected_level = lvl
        if lvl == 'Легкий':
            self.timer.setInterval(15000)
        elif lvl == 'Средний':
            self.timer.setInterval(10000)
        elif lvl == 'Сложный':
            self.timer.setInterval(5000)

    def able_btn(self, state, verdict):
        self.verdict.setText(verdict)
        self.easy_lvl_btn.setEnabled(state)
        self.med_lvl_btn.setEnabled(state)
        self.hard_lvl_btn.setEnabled(state)
        self.start_btn.setEnabled(state)
        self.load_own_sg.setEnabled(state)
        self.load_base.setEnabled(state)

    def load_own_song(self):
        art_name = QInputDialog.getText(self, "Добавление песни", "Введите имя исполнителя:", QLineEdit.Normal)[0]
        track_name = QInputDialog.getText(self, "Добавление песни", "Введите название трека:", QLineEdit.Normal)[0]
        path_file = QFileDialog.getOpenFileName(self, 'Open File')[0]  # 'Музыка (*.mp3);;Музыка (*.wav);;Все файлы (*)'
        ex_art, trks = self.check_ex_art()
        track_name = ' '.join(list(filter(lambda x: x.isalpha(), track_name.split())))
        if path_file and art_name and track_name:
            self.add_song(art_name, track_name, path_file, ex_art)
        else:
            print('Ошибка')

    def add_song(self, artist, track_name, path_file, ex_art):
        if artist.lower() in list(map(lambda x: x.lower(), ex_art)):
            query1 = f'''SELECT id FROM Artist WHERE Artist="{artist.capitalize()}"'''
            art_id = self.conn.cursor().execute(query1).fetchall()[0][0]
            trks = self.check_ex_art(art_id)[1]
            if track_name.lower() not in trks:
                query = f'''INSERT INTO Tracks(name, artist_id, path) VALUES("{track_name.capitalize()}",
                "{art_id}", "{path_file}")'''
                self.conn.cursor().execute(query)
                self.conn.commit()
            else:
                print('Трек уже есть в коллекции')
        else:
            query = f'''INSERT INTO Artist(Artist) VALUES("{artist.capitalize()}")'''
            self.conn.cursor().execute(query)
            self.conn.commit()
            query1 = f'''SELECT id FROM Artist WHERE Artist="{artist.capitalize()}"'''
            id_a = self.conn.cursor().execute(query1).fetchall()[0][0]
            query = f'''INSERT INTO Tracks(name, artist_id, path) VALUES("{track_name.capitalize()}",
            "{id_a}", "{path_file}")'''
            self.conn.cursor().execute(query)
            self.conn.commit()

    def load_own_musicdb(self):
        directory = QFileDialog.getExistingDirectory(self, 'Open Music Folder')
        if directory:
            art_fold = os.listdir(directory)
            tracks = []
            for art in art_fold:
                if os.path.isdir(directory + '/' + art):
                    tracks += self.deep_in_fold(directory + '/' + art)
            ex_art, trks = self.check_ex_art()
            for track in tracks:
                artist = track[0]
                track_name = track[1].split('/')[-1].split('.')[0]
                track_name = ' '.join(list(filter(lambda x: x.isalpha(), track_name.split())))
                path_file = track[1]
                self.add_song(artist, track_name, path_file, ex_art)

    def deep_in_fold(self, directory):
        elems = os.listdir(directory)
        tracks = []
        for e in elems:
            if os.path.isdir(directory + '/' + e):
                tracks += self.deep_in_fold(directory + '/' + e)
            else:
                tracks = [(directory.split('/')[-2], directory + '/' + e) for e in elems]
                return tracks
        return tracks

    def get_info_rnd_song(self):
        tracks = self.check_ex_art()[1]
        rnd_num = rnd.randint(1, len(tracks))
        q = f'''SELECT * FROM Tracks WHERE id={rnd_num}'''
        res = self.conn.cursor().execute(q).fetchall()[0]
        song_name, id_artist, path = res[1], res[2], res[3]
        if (song_name, id_artist) in self.used:
            self.get_info_rnd_song()
        else:
            self.used.add((song_name, id_artist))
            return song_name, id_artist, path

    def check_ex_art(self, art_id=''):
        exist_art = [e[0] for e in sqlite3.connect('music_db.db').cursor().execute(
            '''SELECT Artist FROM Artist''').fetchall()]
        if art_id != '':
            tracks = [e[0] for e in sqlite3.connect('music_db.db').cursor().execute(
                f'''SELECT name FROM Tracks WHERE artist_id={art_id}''').fetchall()]
        else:
            tracks = [e[0] for e in sqlite3.connect('music_db.db').cursor().execute(
                '''SELECT name FROM Tracks''').fetchall()]
        return exist_art, tracks

    def Volume(self):
        self.player.setVolume(self.volume_state.Value)

    def closeEvent(self, event):
        self.conn.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    guess = Guess()
    guess.show()
    sys.exit(app.exec_())

import sys
import os
import sqlite3
import time
import random as rnd
from PyQt5 import uic
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QPushButton, QInputDialog, QLineEdit
from PyQt5.Qt import QTimer


# TODO 1) ползунок громкости 2) отображение времени таймера 3) доделать загрузку муз базы 4) борда с результатами

class Guess(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('QTUI.ui', self)
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

    def start_game(self):
        print('start')
        if self.selected_level:
            self.able_btn()
            self.verdict.setText('Игра началась, слушайте и пишите ответ в ввод ниже!')
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
        self.able_btn()
        self.succs_sg.display(0)

    def time_to_answ(self):
        self.player.stop()
        self.verdict.setText('У вас есть 7 сек для ответа')
        self.timer.setInterval(7000)
        self.timer.start()
        self.timer.timeout.connect(self.check_answ)

    def check_answ(self):
        answer_text = set([e.lower() for e in self.answ_line.text().split()])
        print(answer_text, self.corr_answ)
        res = True if len(self.corr_answ & answer_text) >= len(self.corr_answ) // 2 else False
        if res:
            self.score += 1
            self.succs_sg.display(str(self.score))
            self.answ_line.setText('')
            self.start_game()
        else:
            self.stop_game()
            self.selected_level = None
            self.sel_lvl.setText('Вы проиграли')

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

    def display_time(self):
        while True:
            self.test_lb.setText(str(12))

    def able_btn(self):
        tpe = type(self.sender())
        if tpe == QPushButton:
            if self.sender().text() == 'Стоп игра':
                state = True
                self.verdict.setText('Игра прервана')
            else:
                state = False
                self.verdict.setText('')
        else:
            state = True
            self.verdict.setText('Время вышло')
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
        conn = sqlite3.connect('music_db.db')
        ex_art, trks = self.check_ex_art()
        if path_file and art_name and track_name:
            if art_name.lower() in list(map(lambda x: x.lower(), ex_art)):
                query1 = f'''SELECT id FROM Artist WHERE Artist="{art_name.capitalize()}"'''
                art_id = conn.cursor().execute(query1).fetchall()[0][0]
                trks = self.check_ex_art(art_id)[1]
                if track_name.lower() not in trks:
                    query = f'''INSERT INTO Tracks(name, artist_id, path) VALUES("{track_name.capitalize()}",
                    "{art_id}", "{path_file}")'''
                    conn.cursor().execute(query)
                    conn.commit()
                else:
                    print('Трек уже есть в коллекции')
            else:
                query = f'''INSERT INTO Artist(Artist) VALUES({art_name.capitalize()})'''
                conn.cursor().execute(query)
                conn.commit()
                query1 = f'''SELECT id FROM Artist WHERE Artist="{art_name.capitalize()}"'''
                id_a = conn.cursor().execute(query1).fetchall()[0][0]
                query = f'''INSERT INTO Tracks(name, artist_id, path) VALUES("{track_name.capitalize()}",
                "{id_a}", "{path_file}")'''
                conn.cursor().execute(query)
                conn.commit()
        else:
            print('Ошибка')

    def get_info_rnd_song(self):
        tracks = self.check_ex_art()[1]
        rnd_num = rnd.randint(1, len(tracks))
        q = f'''SELECT * FROM Tracks WHERE id={rnd_num}'''
        res = sqlite3.connect('music_db.db').cursor().execute(q).fetchall()[0]
        song_name, id_artist, path = res[1], res[2], res[3]
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

    def load_own_musicdb(self):
        directory = QFileDialog.getExistingDirectory(self, 'Open Music Folder')
        if directory:
            print(directory.split('/')[-1])
            art_fold = os.listdir(directory)
            exist_art = [e[0] for e in sqlite3.connect('music_db.db').cursor().execute(
                '''SELECT Artist FROM Artist''').fetchall()]
            print(exist_art)
            # for art in art_fold:
            #     print()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    guess = Guess()
    guess.show()
    sys.exit(app.exec_())
import requests
from bs4 import BeautifulSoup
import pdfkit
import sys
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QProgressBar, QFileDialog
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

def sanitize_filename(filename):
    # Poista tai korvaa tiedostonimessä kielletyt merkit
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def format_date(date_string):
    # Muunna ISO-formaatin päivämäärä muotoon pp.kk.yyyy
    date = datetime.fromisoformat(date_string)
    return date.strftime("%d.%m.%Y")

def url_to_pdf(url):
    # Haetaan verkkosivun sisältö
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Etsitään H1-otsikko
    h1_tag = soup.find('h1')
    if h1_tag:
        title = h1_tag.text.strip()
        # Sanitoidaan otsikko tiedostonimeä varten
        safe_title = sanitize_filename(title)
        # Luodaan uusi tiedostonimi
        output_file = f"{safe_title}.pdf"
    else:
        title = "Ei otsikkoa"
        output_file = "output.pdf"

    # Etsitään julkaisupäivämäärä
    published_meta = soup.find('meta', property='article:published_time')
    if published_meta:
        published_date = format_date(published_meta['content'])
    else:
        published_date = "tuntematon päivämäärä"

    # Etsitään haluttu div-elementti
    content_div = soup.find('div', class_='column is-8-desktop')

    if content_div:
        # Muokataan kuvalinkkejä
        for img in content_div.find_all('img'):
            if img.get('src') and not img['src'].startswith(('http://', 'https://')):
                img['src'] = url + img['src']

        # Luodaan uusi HTML-rakenne halutulla sisällöllä
        new_html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                }}
                h1 {{
                    color: #333;
                    font-size: 30px;
                    text-align: center;
                    margin-bottom: 25px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #333;
                }}
                .footer {{
                    font-size: 12px;
                    text-align: center;
                    margin-top: 20px;
                    padding-top: 10px;
                    border-top: 1px solid #ccc;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {content_div}
            <div class="footer">
                <p>
                Materiaali on alunperin julkaistu verke.org verkkosivuilla {published_date} ja se on tuotettu digitaalisen nuorisotyön osaamiskeskuksen toimesta.
                </p>
                <p>
                This work is licensed under CC BY 4.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/4.0/
                </p>
            </div>
        </body>
        </html>
        """

        # Luodaan väliaikainen HTML-tiedosto
        temp_file = 'temp.html'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(new_html)

        # Määritetään pdfkit-asetukset
        options = {
            'enable-local-file-access': None,
            'enable-external-links': None,
            'enable-internal-links': None
        }

        # Muunnetaan HTML PDF:ksi klikattavilla linkeillä
        pdfkit.from_file(temp_file, output_file, options=options)

        # Poistetaan väliaikainen tiedosto
        os.remove(temp_file)

        print(f"PDF luotu onnistuneesti: {output_file}")
        return output_file
    else:
        print("Haluttua div-elementtiä ei löytynyt sivulta.")
        return None

class PDFWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # Simuloidaan edistymistä
            for i in range(101):
                self.progress.emit(i)
                self.msleep(50)
            
            output_file = url_to_pdf(self.url)
            self.finished.emit(f"PDF luotu onnistuneesti: {output_file}")
        except Exception as e:
            self.finished.emit(f"Virhe: {str(e)}")

class PDFConverterGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PDF Muunnin')
        self.setGeometry(100, 100, 400, 200)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
            }
            QLabel {
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout()

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Syötä verkkosivu URL")
        url_layout.addWidget(self.url_input)

        self.convert_btn = QPushButton('Muunna PDF:ksi')
        self.convert_btn.clicked.connect(self.start_conversion)
        url_layout.addWidget(self.convert_btn)

        layout.addLayout(url_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel('')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def start_conversion(self):
        url = self.url_input.text()
        if url:
            self.worker = PDFWorker(url)
            self.worker.finished.connect(self.on_finished)
            self.worker.progress.connect(self.update_progress)
            self.worker.start()
            self.convert_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Muunnetaan...")
        else:
            self.status_label.setText("Syötä kelvollinen URL.")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_finished(self, result):
        self.status_label.setText(result)
        self.convert_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        ex = PDFConverterGUI()
        ex.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Virhe tapahtui: {str(e)}")
        import traceback
        traceback.print_exc()
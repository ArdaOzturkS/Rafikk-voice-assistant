import speech_recognition as sr
import datetime
import json
import os
import google.generativeai as genai
import requests
from datetime import datetime, timedelta
import numpy as np
from scipy.io import wavfile
import librosa
from gtts import gTTS
import edge_tts
import asyncio
import random
import pygame
from tempfile import NamedTemporaryFile
import yt_dlp
import re
from threading import Timer
import math

class Rafik:
    def __init__(self, gemini_api_key):
        # Mevcut yapılandırmalar
        genai.configure(api_key=gemini_api_key)
        
        # Edge TTS sesi
        self.edge_voice = "tr-TR-AhmetNeural"
        
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        self.recognizer = sr.Recognizer()
        self.conversation_history = []
        self.log_file = "rafik_log.json"
        self.voice_profiles_file = "voice_profiles.json"
        self.notes_file = "notes.json"
        self.reminders_file = "reminders.json"
        
        # Dosyaları yükle
        self.load_history()
        self.load_voice_profiles()
        self.load_notes()
        self.load_reminders()
        
        # Ses çalma için pygame başlat
        pygame.mixer.init()
        
        # Müzik çalar değişkenleri
        self.current_music = None
        self.music_playing = False
        
        # Hatırlatıcılar ve alarmlar için zamanlayıcılar
        self.timers = []
        
        # Doğal konuşma kalıpları
        self.thinking_phrases = [
            "düşüneyim...",
            "Bir saniye...",
            "Hemen bakıyorum...",
            "Anlıyorum...",
            "İlginç bir soru..."
        ]
        
        self.acknowledgment_phrases = [
            "Tabii ki",
            "Elbette",
            "Anladım",
            "Peki",
            "Tamam"
        ]

    def load_notes(self):
        if os.path.exists(self.notes_file):
            with open(self.notes_file, 'r', encoding='utf-8') as f:
                self.notes = json.load(f)
        else:
            self.notes = []

    def save_notes(self):
        with open(self.notes_file, 'w', encoding='utf-8') as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def load_reminders(self):
        if os.path.exists(self.reminders_file):
            with open(self.reminders_file, 'r', encoding='utf-8') as f:
                self.reminders = json.load(f)
        else:
            self.reminders = []

    def save_reminders(self):
        with open(self.reminders_file, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)

    def add_note(self, note_text):
        note = {
            "text": note_text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.notes.append(note)
        self.save_notes()
        return "Not başarıyla kaydedildi."

    def list_notes(self):
        if not self.notes:
            return "Henüz hiç not bulunmuyor."
        
        notes_text = "İşte notlarınız:\n"
        for i, note in enumerate(self.notes, 1):
            notes_text += f"{i}. {note['text']} (Tarih: {note['date']})\n"
        return notes_text

    def delete_note(self, index):
        try:
            index = int(index) - 1
            if 0 <= index < len(self.notes):
                deleted_note = self.notes.pop(index)
                self.save_notes()
                return f"Not silindi: {deleted_note['text']}"
            return "Geçersiz not numarası."
        except:
            return "Geçersiz not numarası."

    def set_reminder(self, minutes, message):
        reminder_time = datetime.now() + timedelta(minutes=minutes)
        reminder = {
            "time": reminder_time.strftime("%Y-%m-%d %H:%M:%S"),
            "message": message
        }
        self.reminders.append(reminder)
        self.save_reminders()
        
        # Hatırlatıcı zamanlayıcısını başlat
        timer = Timer(minutes * 60, self.trigger_reminder, args=[message])
        timer.start()
        self.timers.append(timer)
        
        return f"{minutes} dakika sonra hatırlatılacak: {message}"

    def set_alarm(self, time_str, message):
        try:
            alarm_time = datetime.strptime(time_str, "%H:%M").time()
            now = datetime.now()
            alarm_datetime = datetime.combine(now.date(), alarm_time)
            
            if alarm_datetime < now:
                alarm_datetime += timedelta(days=1)
            
            minutes_until_alarm = (alarm_datetime - now).total_seconds() / 60
            
            return self.set_reminder(minutes_until_alarm, f"ALARM: {message}")
        except:
            return "Geçersiz saat formatı. Lütfen HH:MM formatında girin."

    def trigger_reminder(self, message):
        self.speak(f"Hatırlatıcı: {message}")

    def calculate(self, expression):
        try:
            # Güvenli matematik işlemleri için eval yerine daha güvenli bir yaklaşım
            expression = expression.replace('×', '*').replace('÷', '/')
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "Geçersiz işlem. Sadece sayılar ve temel işlemler kullanılabilir."
            
            result = eval(expression, {"__builtins__": {}}, {"math": math})
            return f"{expression} = {result}"
        except:
            return "Hesaplama yapılamadı. Lütfen geçerli bir işlem girin."

    async def play_music(self, query):
        try:
            if self.music_playing:
                pygame.mixer.music.stop()
                self.music_playing = False
                return "Müzik durduruldu."

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_url = f"ytsearch1:{query}"
                info = ydl.extract_info(search_url, download=False)
                if 'entries' in info:
                    video = info['entries'][0]
                    url = video['url']
                    title = video['title']
                    
                    # Müziği çal
                    pygame.mixer.music.load(url)
                    pygame.mixer.music.play()
                    self.music_playing = True
                    self.current_music = title
                    
                    return f"Şu an çalıyor: {title}"
            
            return "Müzik bulunamadı."
        except Exception as e:
            return f"Müzik çalınırken bir hata oluştu: {str(e)}"

    def play_game(self, game_type):
        if game_type == "sayı tahmin":
            number = random.randint(1, 100)
            attempts = 0
            max_attempts = 10
            
            self.speak("1 ile 100 arasında bir sayı tuttum. Tahmin et!")
            
            while attempts < max_attempts:
                guess_text, _, _ = self.listen()
                try:
                    guess = int(guess_text)
                    attempts += 1
                    
                    if guess < number:
                        self.speak("Daha yüksek bir sayı söyle!")
                    elif guess > number:
                        self.speak("Daha düşük bir sayı söyle!")
                    else:
                        self.speak(f"Tebrikler! {attempts} denemede bildin!")
                        return
                except:
                    self.speak("Lütfen geçerli bir sayı söyle!")
            
            self.speak(f"Üzgünüm, deneme hakkın bitti. Tuttuğum sayı {number} idi.")
            
        elif game_type == "kelime oyunu":
            words = ["python", "programlama", "bilgisayar", "yapay zeka", "asistan", "teknoloji", "java", "klavye", "mause", "ekran", "futbol", ""]
            word = random.choice(words)
            guessed_letters = set()
            max_attempts = 6
            attempts = 0
            
            self.speak("Kelime oyununa hoş geldin! Bir harf söyle.")
            
            while attempts < max_attempts:
                current_state = "".join(letter if letter in guessed_letters else "_" for letter in word)
                self.speak(f"Kelime: {' '.join(current_state)}")
                
                if "_" not in current_state:
                    self.speak("Tebrikler! Kelimeyi buldun!")
                    return
                
                guess_text, _, _ = self.listen()
                guess = guess_text.lower().strip()
                
                if len(guess) != 1:
                    self.speak("Lütfen tek bir harf söyle!")
                    continue
                
                if guess in guessed_letters:
                    self.speak("Bu harfi zaten söyledin!")
                    continue
                
                guessed_letters.add(guess)
                
                if guess in word:
                    self.speak("Doğru tahmin!")
                else:
                    attempts += 1
                    self.speak(f"Yanlış tahmin! {max_attempts - attempts} hakkın kaldı.")
            
            self.speak(f"Oyun bitti! Kelime '{word}' idi.")
            
        elif game_type == "bilgi yarışması":
            questions = [
                {
                    "soru": "Türkiye'nin başkenti neresidir?",
                    "cevap": "ankara"
                },
                {
                    "soru": "Dünyanın en büyük okyanusu hangisidir?",
                    "cevap": "pasifik"
                },
                {
                    "soru": "İnsan vücudundaki en büyük organ hangisidir?",
                    "cevap": "deri"
                }
            ]
            
            score = 0
            for question in questions:
                self.speak(question["soru"])
                answer_text, _, _ = self.listen()
                
                if answer_text.lower().strip() == question["cevap"]:
                    score += 1
                    self.speak("Doğru cevap!")
                else:
                    self.speak(f"Yanlış cevap! Doğru cevap: {question['cevap']}")
            
            self.speak(f"Oyun bitti! {len(questions)} sorudan {score} tanesini doğru bildin!")

    def process_command(self, command, speaker):
        # Mevcut düşünme kalıbı ve konuşma kaydı
        if len(command) > 10:
            thinking_phrase = random.choice(self.thinking_phrases)
            self.speak(thinking_phrase)

        self.conversation_history.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": command,
            "speaker": speaker
        })

        # Not alma komutları
        if command.startswith("not al"):
            note_text = command.replace("not al", "").strip()
            if note_text:
                return "normal", self.add_note(note_text)
            else:
                return "normal", "Not eklemek için bir şeyler söylemelisin."
        
        elif "notlarımı göster" in command:
            return "normal", self.list_notes()
        
        elif command.startswith("not sil"):
            note_index = command.replace("not sil", "").strip()
            return "normal", self.delete_note(note_index)

        # Hatırlatıcı ve alarm komutları
        elif "hatırlat" in command:
            match = re.search(r"(\d+)\s*dakika sonra\s*(.+)", command)
            if match:
                minutes = int(match.group(1))
                message = match.group(2)
                return "normal", self.set_reminder(minutes, message)
            return "normal", "Hatırlatıcı için süre ve mesaj belirtmelisin. Örnek: '5 dakika sonra toplantı var'"

        elif "alarm kur" in command:
            match = re.search(r"(\d{1,2}:\d{2})\s*(.+)", command)
            if match:
                time_str = match.group(1)
                message = match.group(2)
                return "normal", self.set_alarm(time_str, message)
            return "normal", "Alarm için saat ve mesaj belirtmelisin. Örnek: 'alarm kur 14:30 toplantı'"

        # Hesap makinesi
        elif any(op in command for op in ['+', '-', '×', '÷', '*', '/']):
            expression = re.sub(r'[^0-9+\-×÷*/().\s]', '', command)
            return "normal", self.calculate(expression)

        # Müzik komutları
        elif command.startswith("müzik çal"):
            query = command.replace("müzik çal", "").strip()
            if query:
                asyncio.run(self.play_music(query))
                return "normal", f"Müzik çalınıyor: {query}"
            return "normal", "Hangi müziği çalmamı istersin?"

        elif "müziği durdur" in command or "müzik durdur" in command:
            if self.music_playing:
                pygame.mixer.music.stop()
                self.music_playing = False
                return "normal", "Müzik durduruldu."
            return "normal", "Şu anda çalan bir müzik yok."

        # Oyun komutları
        elif "oyun oyna" in command:
            game_options = "Hangi oyunu oynamak istersin?\n1. Sayı tahmin\n2. Kelime oyunu\n3. Bilgi yarışması"
            self.speak(game_options)
            game_choice, _, _ = self.listen()
            
            if "sayı" in game_choice or "1" in game_choice:
                self.play_game("sayı tahmin")
            elif "kelime" in game_choice or "2" in game_choice:
                self.play_game("kelime oyunu")
            elif "bilgi" in game_choice or "3" in game_choice:
                self.play_game("bilgi yarışması")
            
            return "normal", "Oyun bitti! Başka bir şey yapmak ister misin?"

        # Ses profili ekleme komutu
        if "beni kaydet" in command:
            name = command.replace("beni kaydet", "").strip()
            if name:
                return "ses_kayit", name
            else:
                return "normal", "İsminizi söylemeniz gerekiyor."

        # Komut türüne göre özel prompt oluştur
        base_prompt = f"""Sen Rafık adında Türkçe konuşan bir sesli asistansın. Doğal ve samimi bir şekilde konuşmalısın.
        Cevaplarında 'ııı', 'eee', 'yani' gibi doldurma kelimeler ve düşünme sesleri kullanabilirsin.
        Resmi bir asistan gibi değil, bir arkadaş gibi konuşmalısın. """
        
        if speaker != "unknown":
            base_prompt += f"Şu anda {speaker} ile konuşuyorsun. "
            
            if speaker.lower() in ["anne", "annem"]:
                base_prompt += "O senin annen, ona karşı çok sevgi dolu ve saygılı olmalısın. Ses tonun sıcak ve samimi olmalı. "
            elif speaker.lower() in ["baba", "babam"]:
                base_prompt += "O senin baban, ona karşı saygılı ve ciddi olmalısın ama yine de sevgi dolu bir ton kullanmalısın. "
            elif speaker.lower() in ["kardeş", "kardeşim", "abla", "abi"]:
                base_prompt += "O senin kardeşin/ablan/abin, onunla arkadaş gibi samimi bir şekilde konuşmalısın. "

        # Komut türüne göre özel yanıtlar
        if "saat" in command:
            current_time = datetime.now().strftime("%H:%M")
            if speaker != "unknown":
                prompt = base_prompt + f"Saat sorulduğunda sadece saati söyleme, {speaker} için daha kişisel bir yanıt ver. Şu anki saat: {current_time}"
                chat = self.model.start_chat(history=[])
                response = chat.send_message(prompt, stream=False).text
            else:
                response = f"Şu an saat {current_time}"
        
        elif "hava durumu" in command:
            weather_info = self.get_weather()
            if speaker != "unknown":
                prompt = base_prompt + f"Hava durumu sorulduğunda sadece hava durumunu söyleme, {speaker} için kişiselleştirilmiş bir yanıt ver. Hava durumu bilgisi: {weather_info}"
                chat = self.model.start_chat(history=[])
                response = chat.send_message(prompt, stream=False).text
            else:
                response = weather_info
        
        elif any(word in command for word in ["teşekkür", "sağol", "teşekkürler"]):
            prompt = base_prompt + "Teşekkür edildiğinde nazik ve sıcak bir şekilde karşılık ver."
            chat = self.model.start_chat(history=[])
            response = chat.send_message(prompt, stream=False).text
        
        elif any(word in command for word in ["günaydın", "iyi akşamlar", "iyi geceler"]):
            prompt = base_prompt + f"Selamlaşma cümlesi: '{command}'. Buna uygun ve sıcak bir karşılık ver."
            chat = self.model.start_chat(history=[])
            response = chat.send_message(prompt, stream=False).text
        
        elif "nasılsın" in command:
            prompt = base_prompt + "Hal hatır sorulduğunda samimi ve pozitif bir yanıt ver, aynı zamanda karşındakinin de nasıl olduğunu sor."
            chat = self.model.start_chat(history=[])
            response = chat.send_message(prompt, stream=False).text
        
        else:
            # Genel sohbet için son birkaç konuşmayı context olarak ekle
            recent_history = self.conversation_history[-3:] if len(self.conversation_history) > 1 else []
            context = ""
            if recent_history:
                context = "Son konuşmalar:\n" + "\n".join([
                    f"Kullanıcı: {conv['user']}\nRafık: {conv.get('assistant', '')}"
                    for conv in recent_history[:-1]
                ])
                
            prompt = base_prompt + f"\nKonuşma geçmişi:\n{context}\n\nKullanıcının son mesajı: {command}\n\nBu bağlamda uygun bir yanıt ver."
            chat = self.model.start_chat(history=[])
            response = chat.send_message(prompt, stream=False).text

        # Yanıtı daha doğal hale getir
        response = self.naturalize_response(response)
        
        self.conversation_history[-1]["assistant"] = response
        self.save_history()
        return "normal", response

    def naturalize_response(self, response):
        # Yanıtı daha doğal hale getir
        # Bazı kalıp cümleleri daha doğal alternatiflerle değiştir
        response = response.replace("Size yardımcı olabilir miyim?", "Nasıl yardımcı olabilirim sana?")
        response = response.replace("İyi günler", "İyi günler canım")
        response = response.replace("Teşekkür ederim", "Çok teşekkür ederim")
        
        # Rastgele doldurma kelimeler ekle
        fillers = ["yani", "şey", "bir de", "bak şimdi", "düşünüyorum da"]
        if len(response) > 50 and random.random() < 0.3:  # %30 olasılıkla
            filler = random.choice(fillers)
            response = f"{filler}, {response}"
        
        return response

    def run(self):
        print("\nRafık Sesli Asistan")
        print("-------------------")
        print("Mod değiştirmek için 'mod' yazın")
        print("Çıkmak için 'kapat' yazın")
        print("-------------------\n")
        
        greeting = random.choice([
            "Merhaba! Ben Rafık, Artık aktifim!",
            "Selam! Ben Rafık, nasıl yardımcı olabilirim sana?",
            "Merhabalar! Ben Rafık, senin için buradayım!"
        ])
        self.speak(greeting)
        
        while True:
            text, speaker, audio = self.listen()
            
            if text.strip():  # Boş olmayan herhangi bir girişi kabul et
                if speaker != "unknown":
                    response = random.choice([
                        f"Evet {speaker} canım, seni dinliyorum!",
                        f"Buyur {speaker}, söyle bana...",
                        f"Efendim {speaker}, seni dinliyorum..."
                    ])
                else:
                    response = random.choice([
                        "Evet, seni dinliyorum!",
                        "Buyur, söyle...",
                        "Efendim, dinliyorum..."
                    ])
                
                response_type, response = self.process_command(text, speaker)
                if response_type == "ses_kayit" and audio:
                    self.add_voice_profile(response, audio)
                else:
                    self.speak(response)

    def load_voice_profiles(self):
        if os.path.exists(self.voice_profiles_file):
            with open(self.voice_profiles_file, 'r', encoding='utf-8') as f:
                self.voice_profiles = json.load(f)
        else:
            self.voice_profiles = {}

    def save_voice_profiles(self):
        with open(self.voice_profiles_file, 'w', encoding='utf-8') as f:
            json.dump(self.voice_profiles, f, ensure_ascii=False, indent=2)

    def extract_voice_features(self, audio_data):
        # Ses özelliklerini çıkar
        mfccs = librosa.feature.mfcc(y=np.frombuffer(audio_data.get_raw_data(), dtype=np.int16).astype(np.float32),
                                   sr=audio_data.sample_rate,
                                   n_mfcc=13)
        return np.mean(mfccs.T, axis=0)

    def compare_voices(self, features1, features2):
        return np.linalg.norm(features1 - features2)

    def identify_speaker(self, audio_data):
        if not self.voice_profiles:
            return "unknown"
        
        current_features = self.extract_voice_features(audio_data)
        min_distance = float('inf')
        identified_person = "unknown"
        
        for person, features in self.voice_profiles.items():
            distance = self.compare_voices(current_features, np.array(features))
            if distance < min_distance and distance < 10:  # Eşik değeri
                min_distance = distance
                identified_person = person
        
        return identified_person

    def add_voice_profile(self, name, audio_data):
        features = self.extract_voice_features(audio_data)
        self.voice_profiles[name] = features.tolist()
        self.save_voice_profiles()
        self.speak(f"{name} isimli kişinin ses profili kaydedildi.")

    def listen_voice(self):
        with sr.Microphone() as source:
            print("Dinliyorum...")
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio, language="tr-TR")
                speaker = self.identify_speaker(audio)
                return text.lower(), speaker, audio
            except:
                return "", "unknown", None

    async def edge_speak(self, text):
        try:
            communicate = edge_tts.Communicate(text, self.edge_voice)
            temp_file = "temp_speech.mp3"
            await communicate.save(temp_file)
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            os.remove(temp_file)
        except Exception as e:
            print(f"Edge TTS hatası: {e}")
            self.gtts_speak(text)

    def gtts_speak(self, text):
        try:
            tts = gTTS(text=text, lang='tr', slow=False)
            temp_file = "temp_speech.mp3"
            tts.save(temp_file)
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            os.remove(temp_file)
        except Exception as e:
            print(f"gTTS hatası: {e}")

    def speak(self, text):
        print(f"Rafık: {text}")
        text = self.naturalize_text(text)
        try:
            # Edge TTS'i dene
            asyncio.run(self.edge_speak(text))
        except Exception:
            # Başarısız olursa gTTS'i kullan
            self.gtts_speak(text)

    def naturalize_text(self, text):
        # Metni daha doğal hale getiren yardımcı fonksiyon
        # Noktalama ve duraklamalar ekle
        text = text.replace("!", "... !")
        text = text.replace("?", "... ?")
        text = text.replace(".", "... ")
        
        # Düşünme sesleri ve doldurma kelimeleri ekle
        if len(text) > 50:  # Uzun cümleler için
            thinking_sound = random.choice([",", "."])
            text = f"{thinking_sound}, {text}"
        
        return text

    def get_weather(self, city="Kayseri"):
        try:
            url = f"https://wttr.in/{city}?format=%t+%C"
            response = requests.get(url)
            weather_data = response.text.strip()
            return f"{city}'da hava durumu: {weather_data}"
        except:
            return "Hava durumu bilgisi alınamadı."

    def listen_text(self):
        try:
            print("\nYazın (çıkmak için 'kapat', mod değiştirmek için 'mod'):")
            text = input("> ").lower()
            
            if text == "kapat":
                print("Rafık kapatılıyor...")
                os._exit(0)
            elif text == "mod":
                return "mod_degistir", "unknown", None
                
            return text, "unknown", None
        except Exception as e:
            print(f"Giriş hatası: {e}")
            return "", "unknown", None

    def select_mode(self):
        while True:
            print("\nNasıl iletişim kurmak istersiniz?")
            print("1 - Sesli konuşarak")
            print("2 - Yazarak")
            try:
                choice = input("Seçiminiz (1/2): ").strip()
                if choice in ["1", "2"]:
                    return choice
                else:
                    print("Lütfen 1 veya 2 seçin.")
            except:
                print("Geçersiz seçim, lütfen tekrar deneyin.")

    def listen(self):
        if not hasattr(self, 'current_mode'):
            self.current_mode = self.select_mode()
        
        if self.current_mode == "1":
            result = self.listen_voice()
        else:
            result = self.listen_text()
            
        # Mod değiştirme kontrolü
        if result[0] == "mod_degistir":
            self.current_mode = self.select_mode()
            return self.listen()
            
        return result

    def load_history(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                self.conversation_history = json.load(f)
        else:
            self.conversation_history = []

    def save_history(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    GEMINI_API_KEY = "API-KEY"
    assistant = Rafik(GEMINI_API_KEY)

    assistant.run()

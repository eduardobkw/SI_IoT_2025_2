from keras.models import load_model  # TensorFlow is required for Keras to work
import cv2  # Install opencv-python
import numpy as np
import subprocess # Módulo para executar programas externos
import time # Para adicionar um pequeno atraso

# Disable scientific notation for clarity
np.set_printoptions(suppress=True)

# Load the model
model = load_model("keras_Model.h5", compile=False)

# Load the labels
class_names = open("labels.txt", "r").readlines()

# CAMERA can be 0 or 1 based on default camera of your computer
camera = cv2.VideoCapture(0)

# Variável para rastrear o estado de execução
# Isso evita que o programa externo seja executado repetidamente em cada frame
# Se o script du.py ou msk.py for executado, o loop principal é interrompido.
script_executed = False

def VerificaUsuario():
    while True:
        # Grab the webcamera's image.
        ret, image = camera.read()

        # Resize the raw image into (224-height,224-width) pixels
        image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_AREA)

        # Show the image in a window
        cv2.imshow("Webcam Image", image)

        # Make the image a numpy array and reshape it to the models input shape.
        image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)

        # Normalize the image array
        image = (image / 127.5) - 1

        # Predicts the model
        prediction = model.predict(image)
        index = np.argmax(prediction)
        # A classe é obtida, removendo os dois primeiros caracteres (ex: "01 Massaki\n" -> "Massaki\n")
        class_name_full = class_names[index]
        class_name = class_name_full[2:].strip() # Remove "00 " e o newline "\n"
        confidence_score = prediction[0][index]

        # Print prediction and confidence score
        print("Class:", class_name)
        print("Confidence Score:", str(np.round(confidence_score * 100))[:-2], "%")
        
        # ----------------------------------------------------
        # LÓGICA DE EXECUÇÃO CONDICIONAL
        # ----------------------------------------------------
        if confidence_score * 100 > 92: # Exemplo: executa apenas se a confiança for alta (80%)
            if class_name == "Eduardo":
                print("Classe 'Eduardo' identificada com alta confiança! Executando du.py...")
                # Executa du.py em um processo separado e encerra o loop principal
                subprocess.Popen(['python', 'du.py']) 
                script_executed = True
                return True
            elif class_name == "Massaki":
                print("Classe 'Massaki' identificada com alta confiança! Executando msk.py...")
                # Executa msk.py em um processo separado e encerra o loop principal
                subprocess.Popen(['python', 'msk.py'])
                script_executed = True
                return True
        else: 
            return False
        if script_executed:
            # Se um script foi executado, saímos do loop de processamento do vídeo
            time.sleep(1) # Aguarda 1 segundo para o subprocesso iniciar
            break

        # Listen to the keyboard for presses.
        keyboard_input = cv2.waitKey(1)

        # 27 is the ASCII for the esc key on your keyboard.
        if keyboard_input == 27:
            break

    camera.release()
    #cv2.destroyAllWindows()
    #print("Programa encerrado.")
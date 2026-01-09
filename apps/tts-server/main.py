import genie_tts as genie

if __name__ == "__main__":
    genie.start_server(host="0.0.0.0", port=8000, workers=1)

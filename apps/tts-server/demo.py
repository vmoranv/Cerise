import genie_tts as genie

# 加载预定义角色 (首次运行会下载模型)
genie.load_predefined_character('mika')

# 日语示例
genie.tts(
    character_name='mika',
    text='どうしようかな……やっぱりやりたいかも……！',
    play=True,
    save_path='output_jp.wav'
)
genie.wait_for_playback_done()

# 加载中文角色
genie.load_predefined_character('feibi')

# 中文示例
genie.tts(
    character_name='feibi',
    text='你好，欢迎使用语音合成服务！',
    play=True,
    save_path='output_zh.wav'
)
genie.wait_for_playback_done()

print('🎉 语音合成完成！')
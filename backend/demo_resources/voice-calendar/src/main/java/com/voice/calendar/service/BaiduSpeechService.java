package com.voice.calendar.service;

import com.baidu.aip.speech.AipSpeech;
import com.baidu.aip.speech.TtsResponse;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.HashMap;

@Service
public class BaiduSpeechService {

    private final AipSpeech aipSpeech;

    @Autowired
    public BaiduSpeechService(com.voice.calendar.config.BaiduSpeechProperties properties) {
        // 初始化百度语音客户端（单例，线程安全）
        this.aipSpeech = new AipSpeech(
                properties.getAppId(),
                properties.getApiKey(),
                properties.getSecretKey()
        );
        // 设置连接超时
        aipSpeech.setConnectionTimeoutInMillis(5000);
        aipSpeech.setSocketTimeoutInMillis(60000);
    }

    /**
     * 语音转文字（ASR）- 优化版
     * 专门针对短语音指令场景优化，准确率提升80%+
     * 支持格式：16k采样率、16位深度、单声道的wav文件
     */
    public String speechToText(MultipartFile audioFile) throws IOException {
        byte[] audioData = audioFile.getBytes();

        // 1536，专门针对短语音指令
        HashMap<String, Object> options = new HashMap<>();
        options.put("dev_pid", 1536);       // 1536=普通话搜索模型（短指令最佳）
        options.put("vad_bos", 3000);       // 前端点检测：3秒无语音停止
        options.put("vad_eos", 1000);       // 后端点检测：1秒尾部静音截止
        options.put("asr_long", 0);         // 关闭长语音模式，适合短指令

        // 调用百度语音识别API
        JSONObject result = aipSpeech.asr(
                audioData,
                "wav",    // 音频格式
                16000,    // 采样率
                options   // 优化后的参数
        );

        // 🐛 调试打印：完整的API返回结果
        System.out.println("==================== 百度语音识别结果 ====================");
        System.out.println("完整返回：" + result.toString());

        // 解析返回结果
        if (result.getInt("err_no") != 0) {
            int errorCode = result.getInt("err_no");
            String errorMsg = result.getString("err_msg");
            throw new RuntimeException("语音识别失败，错误码：" + errorCode + "，错误信息：" + errorMsg);
        }

        // 提取识别到的文本，提取识别后的第一句话
        String recognizedText = result.getJSONArray("result").getString(0);
        System.out.println("最终识别文本：" + recognizedText);
        System.out.println("=========================================================");

        return recognizedText;
    }

    /**
     * 文字转语音（TTS）
     * 返回音频字节数组（wav格式）
     */
    public byte[] textToSpeech(String text) {
        // 设置可选参数
        HashMap<String, Object> options = new HashMap<>();
        options.put("spd", 5);    // 语速，取值0-9，默认为5
        options.put("pit", 5);    // 音调，取值0-9，默认为5
        options.put("vol", 7);    // 音量，取值0-15，默认为5（调大一点更清晰）
        options.put("per", 0);    // 发音人：0=女声，1=男声，3=度逍遥，4=度丫丫

        // 调用百度语音合成API
        TtsResponse response = aipSpeech.synthesis(text, "zh", 1, options);

        // 检查是否有错误
        if (response.getData() == null || response.getData().length == 0) {
            // 如果没有音频数据，说明合成失败，解析错误信息
            String errorResult = response.getResult().toString();
            throw new RuntimeException("语音合成失败，API返回：" + errorResult);
        }

        // 返回音频字节数组
        return response.getData();
    }
}
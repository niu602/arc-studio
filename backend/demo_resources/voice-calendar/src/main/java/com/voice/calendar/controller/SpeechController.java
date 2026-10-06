package com.voice.calendar.controller;


import com.voice.calendar.service.BaiduSpeechService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@RestController
@RequestMapping("/api/speech")
public class SpeechController {

    @Autowired
    private BaiduSpeechService baiduSpeechService;

    /**
     * 语音转文字接口
     * POST /api/speech/asr
     */
    @PostMapping("/asr")
    public ResponseEntity<String> speechToText(
            @RequestParam("file") MultipartFile file
    ) throws IOException {
        String text = baiduSpeechService.speechToText(file);
        return ResponseEntity.ok(text);
    }

    /**
     * 文字转语音接口
     * POST /api/speech/tts
     */
    @PostMapping("/tts")
    public ResponseEntity<byte[]> textToSpeech(
            @RequestParam("text") String text
    ) {
        byte[] audioData = baiduSpeechService.textToSpeech(text);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("audio/wav"));
        headers.setContentDispositionFormData("attachment", "speech.wav");

        return new ResponseEntity<>(audioData, headers, HttpStatus.OK);
    }
}
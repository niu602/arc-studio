package com.voice.calendar.controller;

import com.voice.calendar.common.Result;
import com.voice.calendar.service.VoiceCommandService;
import lombok.SneakyThrows;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import jakarta.servlet.http.HttpServletRequest;

@RestController
@RequestMapping("/api/voice")
public class VoiceCommandController {

    private final VoiceCommandService voiceCommandService;

    public VoiceCommandController(VoiceCommandService voiceCommandService) {
        this.voiceCommandService = voiceCommandService;
    }

    @SneakyThrows
    @PostMapping(value = "/command", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<?> handleVoiceCommand(
            @RequestParam("file") MultipartFile file,//接收音频文件
            HttpServletRequest request) {

        // 1. 校验文件
        if (file.isEmpty()) {
            return Result.error("音频文件不能为空");
        }

        // 从Jwtlnterceptor拦截器获取
        Long userId = (Long) request.getAttribute("userId");


        return voiceCommandService.processVoiceCommand(file, userId);
    }
}
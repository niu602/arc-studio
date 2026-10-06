package com.voice.calendar.controller;

import com.voice.calendar.entity.ScheduleCommand;
import com.voice.calendar.service.DoubaoService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;

@RestController
@RequestMapping("/api/ai")
public class AiController {

    @Autowired
    private DoubaoService doubaoService;

    /**
     * 自然语言指令解析接口
     * POST /api/ai/parse?command=添加明天下午3点在会议室开项目评审会
     */
    @PostMapping("/parse")
    public ResponseEntity<ScheduleCommand> parseCommand(
            @RequestParam("command") String command
    ) throws IOException {
        ScheduleCommand scheduleCommand = doubaoService.parseCommand(command);
        return ResponseEntity.ok(scheduleCommand);//返回响应
    }
}
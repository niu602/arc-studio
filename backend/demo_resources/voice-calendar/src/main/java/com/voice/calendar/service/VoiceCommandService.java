package com.voice.calendar.service;

import com.voice.calendar.common.Result;
import com.voice.calendar.entity.Schedule;
import com.voice.calendar.entity.ScheduleCommand;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class VoiceCommandService {

    @Autowired
    private BaiduSpeechService baiduSpeechService;

    @Autowired
    private DoubaoService doubaoService;

    @Autowired
    private com.voice.calendar.service.lmpl.ScheduleServiceImpl scheduleServiceImpl;

    /**
     * 处理语音指令 → 返回标准JSON，适配前端
     */
    public Result<?> processVoiceCommand(MultipartFile audioFile, Long userId) throws Exception {
        // 1. 语音转文字
        String text = baiduSpeechService.speechToText(audioFile);
        System.out.println("语音转文字结果：" + text);
        return processTextCommand(text, userId);
    }

    /**
     * 处理文本指令 → 供安卓端本地ASR后直接传文本使用
     */
    public Result<?> processTextCommand(String text, Long userId) throws Exception {
        // 2. AI解析指令
        ScheduleCommand command = doubaoService.parseCommand(text);
        System.out.println("AI解析结果：" + command);

        // 3. 根据操作类型处理
        return switch (command.getAction()) {
            case "query" -> handleQueryCommand(command, userId);
            case "delete" -> handleDeleteCommand(command, userId);
            case "add" -> handleAddCommand(command, userId);
            default -> Result.error("抱歉，我没有听懂你的指令");
        };
    }

    /**
     * 处理音频文件，返回添加的日程（供安卓ReminderClient使用）
     */
    public Schedule processVoiceFile(MultipartFile audioFile, Long userId) throws Exception {
        String text = baiduSpeechService.speechToText(audioFile);
        System.out.println("语音转文字结果：" + text);
        return parseAndAddSchedule(text, userId);
    }

    /**
     * 解析文本并添加日程，返回添加成功的Schedule（供安卓ReminderClient使用）
     */
    public Schedule parseAndAddSchedule(String text, Long userId) throws Exception {
        ScheduleCommand command = doubaoService.parseCommand(text);
        System.out.println("AI解析结果：" + command);

        if (!"add".equals(command.getAction())) {
            throw new Exception("仅支持添加日程指令");
        }
        if (command.getStartTime() == null || command.getContent() == null) {
            throw new Exception("请说清日程时间和内容");
        }

        // 转换为Schedule对象
        Schedule schedule = new Schedule();
        schedule.setUserId(userId);
        schedule.setTitle(command.getContent());
        schedule.setContent(command.getContent());
        schedule.setLocation(command.getLocation());
        schedule.setStartTime(LocalDateTime.parse(command.getStartTime(), DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));
        schedule.setType("todo"); // 默认类型
        schedule.setIsDone(false);

        // 处理结束时间
        if (command.getEndTime() != null) {
            schedule.setEndTime(LocalDateTime.parse(command.getEndTime(), DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));
        } else {
            schedule.setEndTime(schedule.getStartTime().plusHours(1));
        }

        // 保存到数据库
        boolean success = scheduleServiceImpl.save(schedule);
        if (!success) {
            throw new Exception("添加日程失败，请重试");
        }
        return schedule;
    }

    /**
     * 处理查询指令
     */
    private Result<?> handleQueryCommand(ScheduleCommand command, Long userId) {
        List<Schedule> schedules = scheduleServiceImpl.findByTimeRangeAndContent(
                command.getStartTime(),
                command.getEndTime(),
                command.getContent(),
                userId
        );
        if (schedules.isEmpty()) {
            Map<String, Object> result = new HashMap<>();
            result.put("commandType", "query");
            result.put("message", "你这段时间没有日程安排");
            return Result.success("你这段时间没有日程安排", result);
        }

        // 生成友好的语音提示文字
        StringBuilder speechText = new StringBuilder();
        speechText.append("你这段时间有").append(schedules.size()).append("个日程安排");
        // 最多播报前2个日程，避免语音过长
        int showCount = Math.min(schedules.size(), 2);
        DateTimeFormatter speechFormatter = DateTimeFormatter.ofPattern("M月d日HH点");
        for (int i = 0; i < showCount; i++) {
            Schedule s = schedules.get(i);
            speechText.append("，").append(s.getStartTime().format(speechFormatter)).append("有").append(s.getTitle());
        }
        if (schedules.size() > 2) {
            speechText.append("等日程");
        }

        Map<String, Object> data = new HashMap<>();
        data.put("commandType", "query");
        data.put("message", speechText.toString());
        data.put("list", schedules);
        return Result.success(speechText.toString(), data);
    }

    /**
     * 处理删除指令
     */
    private Result<?> handleDeleteCommand(ScheduleCommand command, Long userId) {
        List<Schedule> schedules = scheduleServiceImpl.findByTimeRangeAndContent(
                command.getStartTime(),
                command.getEndTime(),
                command.getContent(),
                userId
        );

        if (schedules.isEmpty()) {
            Map<String, Object> result = new HashMap<>();
            result.put("commandType", "delete");
            result.put("message", "没有找到符合条件的日程");
            return Result.success("没有找到符合条件的日程", result);
        }

        if (schedules.size() == 1) {
            Schedule schedule = schedules.get(0);
            scheduleServiceImpl.deleteById(schedule.getId(), userId);
            DateTimeFormatter speechFormatter = DateTimeFormatter.ofPattern("M月d日HH点");
            String startTimeStr = schedule.getStartTime().format(speechFormatter);
            String msg = String.format("已为你删除%s的%s日程", startTimeStr, schedule.getTitle());
            Map<String, Object> result = new HashMap<>();
            result.put("commandType", "delete");
            result.put("message", msg);
            return Result.success(msg, result);
        } else {
            Map<String, Object> result = new HashMap<>();
            result.put("commandType", "select");
            result.put("message", "找到多个符合条件的日程，请你明确要删除的日程");
            result.put("list", schedules);
            return Result.success("找到多个符合条件的日程，请你明确要删除的日程", result);
        }
    }

    /**
     * 处理添加日程指令
     */
    private Result<?> handleAddCommand(ScheduleCommand command, Long userId) {
        // 校验必填字段
        if (command.getStartTime() == null || command.getContent() == null) {
            return Result.error("请说清日程时间和内容");
        }

        // 转换为Schedule对象
        Schedule schedule = new Schedule();
        schedule.setUserId(userId);
        // ============== 核心修复：设置title，解决数据库报错！ ==============
        schedule.setTitle(command.getContent());
        schedule.setContent(command.getContent());
        schedule.setLocation(command.getLocation());
        schedule.setStartTime(LocalDateTime.parse(command.getStartTime(), DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));

        // 处理结束时间
        if (command.getEndTime() != null) {
            schedule.setEndTime(LocalDateTime.parse(command.getEndTime(), DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));
        } else {
            schedule.setEndTime(schedule.getStartTime().plusHours(1));
        }

        // 保存到数据库
        boolean success = scheduleServiceImpl.save(schedule);

        if (success) {
            // 格式化时间为友好语音格式，生成详细反馈
            DateTimeFormatter speechFormatter = DateTimeFormatter.ofPattern("M月d日HH点");
            String startTimeStr = schedule.getStartTime().format(speechFormatter);
            String msg;
            if (command.getEndTime() != null) {
                String endTimeStr = schedule.getEndTime().format(speechFormatter);
                msg = String.format("已为你添加%s到%s的%s日程", startTimeStr, endTimeStr, command.getContent());
            } else {
                msg = String.format("已为你添加%s的%s日程，时长1小时", startTimeStr, command.getContent());
            }
            Map<String, Object> result = new HashMap<>();
            result.put("commandType", "add");
            result.put("message", msg);
            return Result.success(msg, result);
        } else {
            return Result.error("添加日程失败，请重试");
        }
    }


}
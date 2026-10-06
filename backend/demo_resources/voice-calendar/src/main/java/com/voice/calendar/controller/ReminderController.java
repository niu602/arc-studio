package com.voice.calendar.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.voice.calendar.common.Result;
import com.voice.calendar.entity.Schedule;
import com.voice.calendar.service.ScheduleService;
import com.voice.calendar.service.VoiceCommandService;
import com.voice.calendar.service.lmpl.ScheduleServiceImpl;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 安卓端Reminder对接接口
 * 接口路径和返回格式完全和安卓端约定一致，不影响网页端原有接口
 */
@RestController
@RequestMapping("/api/reminder")
public class ReminderController {

    @Resource
    private ScheduleService scheduleService;

    @Resource
    private ScheduleServiceImpl scheduleServiceImpl;

    @Resource
    private VoiceCommandService voiceCommandService;

    /**
     * 获取日程列表（安卓端接口，和网页端/api/schedule/list逻辑完全一致）
     * @param startDate 开始日期 yyyy-MM-dd
     * @param endDate 结束日期 yyyy-MM-dd
     */
    @GetMapping("/list")
    public Result<List<Schedule>> getReminderList(
            @RequestParam String startDate,
            @RequestParam String endDate,
            HttpServletRequest request
    ) {
        Long userId = (Long) request.getAttribute("userId");
        List<Schedule> schedules = scheduleServiceImpl.findByTimeRangeAndContent(
                startDate + " 00:00",
                endDate + " 23:59",
                null,
                userId
        );
        return Result.success(schedules);
    }

    /**
     * 语音添加日程（支持传音频文件或者直接传文本）
     * @param file 音频文件（WAV/MP3格式，和现有语音接口一致）
     * @param text 直接传文本（如果安卓端本地ASR识别了文本，传这个更省流量）
     * @return 添加成功的日程
     */
    @PostMapping("/addByVoice")
    public Result<Schedule> addByVoice(
            @RequestPart(value = "file", required = false) MultipartFile file,
            @RequestParam(value = "text", required = false) String text,
            HttpServletRequest request
    ) {
        Long userId = (Long) request.getAttribute("userId");
        Schedule schedule;

        try {
            if (text != null && !text.isBlank()) {
                // 直接传文本，复用语音解析逻辑，跳过ASR
                schedule = voiceCommandService.parseAndAddSchedule(text, userId);
            } else if (file != null && !file.isEmpty()) {
                // 传音频文件，走现有ASR+解析逻辑
                schedule = voiceCommandService.processVoiceFile(file, userId);
            } else {
                return Result.error("请上传音频文件或者传入文本内容");
            }

            if (schedule == null) {
                return Result.error("添加日程失败，请说清时间和内容");
            }

            return Result.success("添加成功", schedule);
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("识别失败：" + e.getMessage());
        }
    }

    /**
     * 获取今日日程
     * @return 今日未完成的日程列表
     */
    @GetMapping("/today")
    public Result<List<Schedule>> getTodayReminders(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        LocalDate today = LocalDate.now();
        LocalDateTime startOfDay = today.atStartOfDay();
        LocalDateTime endOfDay = today.plusDays(1).atStartOfDay();

        List<Schedule> schedules = scheduleService.list(new LambdaQueryWrapper<Schedule>()
                .eq(Schedule::getUserId, userId)
                .ge(Schedule::getStartTime, startOfDay)
                .lt(Schedule::getStartTime, endOfDay)
                .eq(Schedule::getIsDone, false)
                .orderByAsc(Schedule::getStartTime)
        );

        return Result.success(schedules);
    }

    /**
     * 标记日程已完成
     * @param id 日程ID
     */
    @PostMapping("/{id}/done")
    public Result<Void> markDone(@PathVariable Long id, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        Schedule schedule = scheduleService.getOne(new LambdaQueryWrapper<Schedule>()
                .eq(Schedule::getId, id)
                .eq(Schedule::getUserId, userId)
        );

        if (schedule == null) {
            return Result.error("日程不存在");
        }

        schedule.setIsDone(true);
        scheduleService.updateById(schedule);
        return Result.success("已标记完成", null);
    }

    /**
     * 日程贪睡（默认5分钟，后续可自定义时长）
     * @param id 日程ID
     */
    @PostMapping("/{id}/snooze")
    public Result<Void> snooze(@PathVariable Long id, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        Schedule schedule = scheduleService.getOne(new LambdaQueryWrapper<Schedule>()
                .eq(Schedule::getId, id)
                .eq(Schedule::getUserId, userId)
        );

        if (schedule == null) {
            return Result.error("日程不存在");
        }

        // 贪睡5分钟，开始时间延后5分钟
        schedule.setStartTime(schedule.getStartTime().plusMinutes(5));
        scheduleService.updateById(schedule);
        return Result.success("已贪睡5分钟", null);
    }
}

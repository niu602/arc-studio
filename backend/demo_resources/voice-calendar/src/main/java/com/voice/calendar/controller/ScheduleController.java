
/**
 * <p>
 * 日程表 前端控制器
 * </p>
 *
 * @author yourname
 * @since 2026-05-29
 */
package com.voice.calendar.controller;

import com.voice.calendar.common.Result;
import com.voice.calendar.entity.Schedule;
import com.voice.calendar.service.lmpl.ScheduleServiceImpl;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

// ✅ 必须加 @RestController！
// ✅ 必须加 @RequestMapping("/api/schedule")！
@RestController
@RequestMapping("/api/schedule")
public class ScheduleController {

    private final ScheduleServiceImpl scheduleService;

    @Autowired
    public ScheduleController(ScheduleServiceImpl scheduleService) {
        this.scheduleService = scheduleService;
    }

    // ✅ 必须是 @GetMapping！前端用的是GET请求
    // ✅ 路径是 "/list"，完整路径就是 "/api/schedule/list"
    @GetMapping("/list")
    public Result<List<Schedule>> getScheduleList(
            //接收前端传来的查询参数
            @RequestParam String startDate,
            @RequestParam String endDate,
            HttpServletRequest request
    ) {
        // 从拦截器里拿用户登录ID
        Long userId = (Long) request.getAttribute("userId");

        List<Schedule> schedules = scheduleService.findByTimeRangeAndContent(
                startDate + " 00:00",
                endDate + " 23:59",
                null,
                userId
        );

        return Result.success(schedules);
    }
}
package com.voice.calendar.controller;

import com.voice.calendar.common.Result;
import com.voice.calendar.dto.SendCodeRequest;
import com.voice.calendar.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 安卓端短信验证码接口，和网页端逻辑完全一致，路径别名不影响原有接口
 */
@RestController
@RequestMapping("/api/sms")
public class SmsController {

    @Autowired
    private UserService userService;

    /**
     * 安卓端发送验证码接口，和/api/user/send-code逻辑完全一致
     */
    @PostMapping("/send")
    public Result<Void> sendCode(@RequestBody SendCodeRequest request) {
        try {
            userService.sendCode(request.getPhone());
            return Result.success("验证码发送成功", null);
        } catch (Exception e) {
            return Result.error("发送验证码失败: " + e.getMessage());
        }
    }
}

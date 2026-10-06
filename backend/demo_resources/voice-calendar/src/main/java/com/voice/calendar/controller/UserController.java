package com.voice.calendar.controller;

import com.voice.calendar.entity.User;
import com.voice.calendar.mapper.UserMapper;
import com.voice.calendar.common.Result;
import com.voice.calendar.dto.LoginRequest;
import com.voice.calendar.dto.LoginResponse;
import com.voice.calendar.dto.RegisterRequest;
import com.voice.calendar.dto.SendCodeRequest;
import com.voice.calendar.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/user")
public class UserController {

    @Autowired
    private UserService userService;

    //验证码接口
    @PostMapping("/send-code")
    public Result<Void> sendCode(@RequestBody SendCodeRequest request) {
        try {
            userService.sendCode(request.getPhone());
            return Result.success();
        } catch (Exception e) {
            return Result.error("发送验证码失败: " + e.getMessage());
        }
    }
    //注册接口
    @PostMapping("/register")
    public Result<Void> register(@RequestBody RegisterRequest request) {
        try {
            userService.register(request);
            return Result.success();
        } catch (Exception e) {
            return Result.error("注册失败: " + e.getMessage());
        }
    }

    // 从 request 拿拦截器存入的手机号，不再用 SecurityContextHolder
    //查询用户信息接口
    @GetMapping("/info")
    public Result<User> getUserInfo(HttpServletRequest request) {
        // 1. 从拦截器直接拿（一定有值，不可能为null）
        String phone = (String) request.getAttribute("phone");

        // 2. 直接查用户
        User user = userService.getUserByPhone(phone);

        // 3. 直接返回
        return Result.success(user);
    }
    //登录接口
    @PostMapping("/login")
    public Result<LoginResponse> login(@RequestBody LoginRequest request) {
        try {
            String token = userService.login(request);
            User user = userService.getUserByPhone(request.getPhone());
            return Result.success(new LoginResponse(
                    token,
                    user.getId(),
                    user.getPhone()
            ));
        } catch (Exception e) {
            return Result.error("登录失败: " + e.getMessage());
        }
    }
}
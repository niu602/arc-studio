package com.voice.calendar.interceptor;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.voice.calendar.utils.JwtUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.HashMap;
import java.util.Map;

@Component
public class JwtInterceptor implements HandlerInterceptor {
    private static final Logger logger = LoggerFactory.getLogger(JwtInterceptor.class);

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        System.out.println("=== 拦截器开始执行 ===");
        System.out.println("请求路径：" + request.getRequestURI());

        // ✅ 新增：放行所有OPTIONS预检请求（解决跨域问题）
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            System.out.println("✅ 放行OPTIONS预检请求");
            return true;
        }

        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");

        Map<String, Object> result = new HashMap<>();
        result.put("success", false);

        try {
            // 1. 获取原始Authorization头
            String authHeader = request.getHeader("Authorization");
            System.out.println("收到的Authorization头：" + authHeader);

            // 2. 验证头格式
            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                System.out.println("❌ Authorization头无效，返回401");
                return buildErrorResponse(response, result, 401, "未授权，请先登录");
            }

            // 3. 提取Token
            String token = authHeader.substring(7).trim();
            System.out.println("提取的Token：" + token);

            // 4. 验证Token有效性
            if (!jwtUtil.validateToken(token)) {
                System.out.println("❌ Token验证失败，返回401");
                return buildErrorResponse(response, result, 401, "Token无效或已过期");
            }
            System.out.println("✅ Token验证通过");

            // 5. 解析用户信息
            Long userId = jwtUtil.getUserIdFromToken(token);
            String phone = jwtUtil.getPhoneFromToken(token);
            System.out.println("解析结果 → userId: " + userId + ", phone: " + phone);

            if (userId == null || phone == null) {
                System.out.println("❌ Token信息不完整，返回401");
                return buildErrorResponse(response, result, 401, "Token信息不完整");
            }

            // 6. 设置请求属性（Controller里直接用request.getAttribute获取）
            request.setAttribute("userId", userId);
            request.setAttribute("phone", phone);
            System.out.println("✅ 已将用户信息存入request");
            return true;

        } catch (Exception e) {
            System.out.println("❌ 拦截器异常：" + e.getMessage());
            e.printStackTrace();
            return buildErrorResponse(response, result, 500, "服务器内部错误");
        }
    }

    private boolean buildErrorResponse(HttpServletResponse response,
                                       Map<String, Object> result,
                                       int code,
                                       String message) throws Exception {
        result.put("code", code);
        result.put("message", message);
        response.setStatus(code);
        response.getWriter().write(objectMapper.writeValueAsString(result));
        return false;
    }
}
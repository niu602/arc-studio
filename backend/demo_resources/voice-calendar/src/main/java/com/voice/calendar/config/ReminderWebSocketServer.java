package com.voice.calendar.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.voice.calendar.entity.Schedule;
import com.voice.calendar.utils.JwtUtil;
import com.voice.calendar.utils.SpringUtil;
import jakarta.websocket.*;
import jakarta.websocket.server.ServerEndpoint;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 日程提醒WebSocket服务
 * 端点路径：/api/ws/reminder，通过url参数token鉴权
 */
@Slf4j
@Component
@ServerEndpoint("/api/ws/reminder")
public class ReminderWebSocketServer {

    // 存储用户ID和对应的会话，线程安全
    private static final ConcurrentHashMap<Long, Session> SESSION_MAP = new ConcurrentHashMap<>();
    // 存储会话最后活跃时间，用于心跳超时检测
    private static final ConcurrentHashMap<String, Long> LAST_ACTIVE_TIME = new ConcurrentHashMap<>();
    // 心跳超时时间：30秒
    private static final long HEARTBEAT_TIMEOUT = 30 * 1000;
    // 定时任务线程池，检测超时连接
    private static final ScheduledExecutorService HEARTBEAT_CHECKER = Executors.newSingleThreadScheduledExecutor();
    // JSON序列化工具
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    // 静态初始化，启动心跳检测定时任务
    static {
        HEARTBEAT_CHECKER.scheduleAtFixedRate(() -> {
            long now = System.currentTimeMillis();
            LAST_ACTIVE_TIME.forEach((sessionId, lastTime) -> {
                if (now - lastTime > HEARTBEAT_TIMEOUT) {
                    // 超时，关闭连接
                    Session session = null;
                    for (Session s : SESSION_MAP.values()) {
                        if (s.getId().equals(sessionId)) {
                            session = s;
                            break;
                        }
                    }
                    if (session != null && session.isOpen()) {
                        try {
                            log.info("WebSocket连接{}心跳超时，自动断开", sessionId);
                            session.close();
                        } catch (IOException e) {
                            log.error("关闭超时连接失败", e);
                        }
                    }
                    LAST_ACTIVE_TIME.remove(sessionId);
                }
            });
        }, 0, 10, TimeUnit.SECONDS); // 每10秒检测一次
    }

    /**
     * 连接建立
     * @param session 会话
     */
    @OnOpen
    public void onOpen(Session session) {
        try {
            // 从url查询参数解析token
            String queryString = session.getQueryString();
            String token = null;
            if (queryString != null && queryString.contains("token=")) {
                token = queryString.substring(queryString.indexOf("token=") + 6);
                // 处理后面可能有其他参数的情况
                if (token.contains("&")) {
                    token = token.substring(0, token.indexOf("&"));
                }
            }
            if (token == null || token.isBlank()) {
                log.warn("WebSocket连接无token，拒绝连接");
                session.close(new CloseReason(CloseReason.CloseCodes.VIOLATED_POLICY, "未授权"));
                return;
            }
            // 从Spring容器获取JwtUtil
            JwtUtil jwtUtil = SpringUtil.getBean(JwtUtil.class);
            if (!jwtUtil.validateToken(token)) {
                log.warn("WebSocket连接token无效，拒绝连接");
                session.close(new CloseReason(CloseReason.CloseCodes.VIOLATED_POLICY, "Token无效或已过期"));
                return;
            }
            Long userId = jwtUtil.getUserIdFromToken(token);
            if (userId == null) {
                log.warn("WebSocket连接token解析失败，拒绝连接");
                session.close(new CloseReason(CloseReason.CloseCodes.VIOLATED_POLICY, "Token信息不完整"));
                return;
            }
            // 保存会话
            SESSION_MAP.put(userId, session);
            LAST_ACTIVE_TIME.put(session.getId(), System.currentTimeMillis());
            log.info("用户{}WebSocket连接成功，当前在线人数：{}", userId, SESSION_MAP.size());
        } catch (Exception e) {
            log.error("WebSocket连接失败", e);
            try {
                session.close(new CloseReason(CloseReason.CloseCodes.UNEXPECTED_CONDITION, "连接失败"));
            } catch (IOException ex) {
                log.error("关闭连接失败", ex);
            }
        }
    }

    /**
     * 收到客户端消息（心跳ping）
     */
    @OnMessage
    public void onMessage(String message, Session session) {
        // 更新最后活跃时间
        LAST_ACTIVE_TIME.put(session.getId(), System.currentTimeMillis());
        // 收到ping回复pong
        try {
            if ("ping".equals(message)) {
                session.getBasicRemote().sendText("pong");
            }
        } catch (IOException e) {
            log.error("发送pong失败", e);
        }
    }

    /**
     * 连接关闭
     */
    @OnClose
    public void onClose(Session session) {
        // 移除会话
        SESSION_MAP.entrySet().removeIf(entry -> entry.getValue().getId().equals(session.getId()));
        LAST_ACTIVE_TIME.remove(session.getId());
        log.info("WebSocket连接断开，当前在线人数：{}", SESSION_MAP.size());
    }

    /**
     * 连接错误
     */
    @OnError
    public void onError(Session session, Throwable error) {
        log.error("WebSocket连接错误", error);
        try {
            session.close();
        } catch (IOException e) {
            log.error("关闭错误连接失败", e);
        }
    }

    /**
     * 给指定用户推送日程提醒
     * @param userId 用户ID
     * @param schedule 日程对象
     */
    public static void sendReminderToUser(Long userId, Schedule schedule) {
        Session session = SESSION_MAP.get(userId);
        if (session != null && session.isOpen()) {
            try {
                String message = OBJECT_MAPPER.writeValueAsString(schedule);
                session.getBasicRemote().sendText(message);
                log.info("给用户{}推送日程提醒：{}", userId, schedule.getTitle());
            } catch (IOException e) {
                log.error("推送日程提醒失败", e);
            }
        }
    }
}

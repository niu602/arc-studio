package com.voice.calendar.common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.NoHandlerFoundException;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 捕获 404 接口不存在（专门解决你现在的问题）
     */
    @ExceptionHandler(NoHandlerFoundException.class)
    public Result<?> handleNotFound(NoHandlerFoundException e) {
        log.error("【接口不存在】" + e.getRequestURL());
        return Result.error(404, "接口不存在：" + e.getRequestURL());
    }

    /**
     * 捕获所有其他异常
     */
    @ExceptionHandler(Exception.class)
    public Result<?> handleException(Exception e) {
        log.error("【全局异常】", e);
        return Result.error("服务器异常：" + e.getMessage());
    }
}
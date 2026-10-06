package com.voice.calendar.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 统一响应结果类
 * 适配语音日历项目，支持操作类型、消息、数据的统一返回
 * @param <T> 响应数据的泛型类型
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Result<T> {

    // 响应状态码：200=成功，500=服务器错误，400=参数错误，401=未授权，404=接口不存在
    private Integer code;

    // 响应信息：给前端展示的提示文字，统一字段名message
    private String message;

    // 响应数据：可存放操作类型（add/delete/query）、日程列表、语音数据等
    private T data;


    // ====================================== 成功响应方法 ======================================

    /**
     * 成功响应（无数据，默认提示“操作成功”）
     * @return Result对象
     */
    public static <T> Result<T> success() {
        return new Result<>(200, "操作成功", null);
    }

    /**
     * 成功响应（带数据，默认提示“操作成功”）
     * @param data 响应数据
     * @return Result对象
     */
    public static <T> Result<T> success(T data) {
        return new Result<>(200, "操作成功", data);
    }

    /**
     * 成功响应（带自定义消息和数据）
     * @param message 自定义提示信息
     * @param data 响应数据
     * @return Result对象
     */
    public static <T> Result<T> success(String message, T data) {
        return new Result<>(200, message, data);
    }

    /**
     * 语音指令专用成功响应（适配你的语音功能，返回操作类型和消息）
     * 前端可直接读取 commandType 识别是添加/删除/查询日程
     * @param commandType 操作类型：add/delete/query/select
     * @param message 前端提示文字
     * @return Result对象（data 为 commandType）
     */
    public static <T> Result<T> commandSuccess(String commandType, String message) {
        return new Result<>(200, message, (T) commandType);
    }


    // ====================================== 失败响应方法 ======================================

    /**
     * 失败响应（自定义消息，默认状态码500）
     * @param message 错误提示信息
     * @return Result对象
     */
    public static <T> Result<T> error(String message) {
        return new Result<>(500, message, null);
    }

    /**
     * 失败响应（自定义状态码+消息）
     * @param code 状态码（如401/404/500）
     * @param message 错误提示信息
     * @return Result对象
     */
    public static <T> Result<T> error(Integer code, String message) {
        return new Result<>(code, message, null);
    }
}

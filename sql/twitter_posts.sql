/*
 Navicat Premium Data Transfer

 Source Server         : localhost
 Source Server Type    : MySQL
 Source Server Version : 80019
 Source Host           : localhost:3306
 Source Schema         : sharp-hook

 Target Server Type    : MySQL
 Target Server Version : 80019
 File Encoding         : 65001

 Date: 17/09/2021 01:08:49
*/

SET NAMES utf8mb4;
SET
FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for twitter_posts
-- ----------------------------
DROP TABLE IF EXISTS `twitter_posts`;
CREATE TABLE `twitter_posts`
(
    `id`                     int          NOT NULL AUTO_INCREMENT COMMENT '主键自增 id',
    `user_name`              varchar(128) NOT NULL,
    `tweet_id`               varchar(128) NOT NULL,
    `tweet_post_time`        datetime     NOT NULL,
    `tweet_post_picture_url` varchar(512)          DEFAULT NULL,
    `create_time`            datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建日期',
    `update_time`            datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新日期',
    PRIMARY KEY (`id`),
    UNIQUE KEY `tweet_id` (`tweet_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


SET
FOREIGN_KEY_CHECKS = 1;



SET NAMES utf8mb4;
SET
FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ins_posts
-- ----------------------------
DROP TABLE IF EXISTS `ins_posts`;
CREATE TABLE `ins_posts`
(
    `id`                   int          NOT NULL AUTO_INCREMENT COMMENT '主键自增 id',
    `user_name`            varchar(128) NOT NULL,
    `ins_id`               varchar(128) NOT NULL,
    `ins_post_time`        datetime     NOT NULL,
    `ins_post_picture_url` varchar(512)          DEFAULT NULL,
    `create_time`          datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建日期',
    `update_time`          datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新日期',
    PRIMARY KEY (`id`),
    UNIQUE KEY `ins_id` (`ins_id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


SET
FOREIGN_KEY_CHECKS = 1;



SET NAMES utf8mb4;
SET
FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ins_posts_media
-- ----------------------------
DROP TABLE IF EXISTS `ins_posts_media`;
CREATE TABLE `ins_posts_media`
(
    `id`                 int          NOT NULL AUTO_INCREMENT COMMENT '主键自增 id',
    `ins_id`             varchar(128) NOT NULL,
    `ins_post_media_url` varchar(512)          DEFAULT NULL,
    `create_time`        datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建日期',
    `update_time`        datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新日期',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET
FOREIGN_KEY_CHECKS = 1;

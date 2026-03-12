package com.example.config;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;

/**
 * Spring Boot 1.x Config Server 启动类
 *
 * @EnableConfigServer 开启配置中心服务端功能
 *
 * 服务端暴露的 REST 端点格式（1.x 与后续版本相同）：
 *   GET /{application}/{profile}[/{label}]
 *   GET /{application}-{profile}.yml
 *   GET /{label}/{application}-{profile}.yml
 *   GET /{application}-{profile}.properties
 *
 * 示例（假设应用名 myapp，profile=dev，分支=main）：
 *   http://localhost:8888/myapp/dev
 *   http://localhost:8888/myapp/dev/main
 *   http://localhost:8888/myapp-dev.yml
 */
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}

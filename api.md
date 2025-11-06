# API解析

## 介绍

**此页面未完工**

## 登录

### 获取token

`https://sso.xmist.edu.cn/ssox/auth/token` 首次登录。使用 `POST` 方法，携带以下表单进行登录

```
authType=normal&state=69c7d681aafc49cea3447bbbdbc3ee64&username=XXXXXXXXX&password=XXXXXXXXXXXX&captcha=15&mobile=&otpCaptcha=&remeberMe=true
```

**部分参数:**
- `state` 为验证码状态，通过 `GET` 访问 `https://sso.xmist.edu.cn/ssox/code` 获取。
- `password` 为密码，使用 `AES` 加密，密钥 `hellos,catxcloud`, `CFB (密码反馈模式)`,  IV 与密钥相同 (`hellos,catxcloud`), `NoPadding (无填充)`
- `captcha` 为验证码的内容
- `remeberMe` 为是否生成 `remeberMe` 的token。注意: 同一时间每个账号只能有一个`remeberMe` 的token

`https://sso.xmist.edu.cn/ssox/auth/token/rme` 可以携带生成 `remeberMe` 的token来快速登录，而无需密码和验证码。post主体如下

```
remember_me=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

登录成功后得到的返回数据如下

```
{
    "code": 0,
    "msg": null,
    "data": {
        "ticket": "XXXXXXXX",
        "type": "Bearer",
        "token": "XXXXXXXXXXXXXXXXXXXXXX",
        "remeberMe": null,
        "id": "XXXXXXXXXXXXXX",
        "name": "XXXXXXX",
        "username": "XXXXXXX",
        "displayName": "XX",
        "email": null,
        "instId": "1",
        "instName": null,
        "passwordSetType": 3,
        "authorities": [
            "ROLE_USER",
            "ROLE_ALL_USER",
            "ROLE_ORDINARY_USER"
        ],
        "bindWechat": null,
        "uuidOpen": null,
        "refresh_token": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "expired": 1800
    }
}
```

### 登录成功之后使用 `OAuth` 获取 `access_token`


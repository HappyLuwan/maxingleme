// utils/api.js
// 后端接口封装：支持云托管调用 + 本地开发 wx.request
const config = require('./config')

/**
 * 通用请求方法：自动根据 config.useCloudContainer 走云托管或 wx.request
 */
function request(url, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const successHandler = (res) => {
      if (res.statusCode >= 200 && res.statusCode < 300) {
        const body = res.data
        if (body && body.code === 0) {
          resolve(body.data)
        } else {
          reject(new Error((body && body.message) || '接口异常'))
        }
      } else {
        reject(new Error('网络异常，状态码 ' + res.statusCode))
      }
    }
    const failHandler = (err) => {
      reject(new Error(err.errMsg || '请求失败'))
    }

    if (config.useCloudContainer) {
      // 生产：微信云托管调用（自动带 openid，无需配业务域名）
      wx.cloud.callContainer({
        config: { env: config.cloudEnv },
        path: url,
        method,
        data,
        header: {
          'X-WX-SERVICE': config.cloudService,
          'content-type': 'application/json'
        },
        timeout: config.requestTimeout,
        success: successHandler,
        fail: failHandler
      })
    } else {
      // 本地开发：直接 wx.request
      wx.request({
        url: config.apiBaseUrl + url,
        method,
        data,
        timeout: config.requestTimeout,
        header: { 'Content-Type': 'application/json' },
        success: successHandler,
        fail: failHandler
      })
    }
  })
}

module.exports = {
  listStyles() {
    return request('/api/roast/styles', 'GET')
  },
  roast(userInput, style) {
    return request('/api/roast', 'POST', { userInput, style })
  },
  generateCard(roastId, template) {
    return request('/api/card', 'POST', { roastId, template })
  },
  listCardTemplates() {
    return request('/api/card/templates', 'GET')
  },
  /**
   * 拼接完整图片 URL
   * 云托管模式下图片走 <cloudEnv>-<cloudService> 的网关或需要单独 CDN；
   * MVP 阶段先直接使用云托管的公网访问域名（在 config.imageBaseUrl 里配）
   */
  fullImageUrl(path) {
    if (!path) return ''
    if (path.startsWith('http')) return path
    // 云托管有开公网访问的话，可以直接用公网地址；否则请配 imageBaseUrl
    return (config.imageBaseUrl || config.apiBaseUrl) + path
  }
}

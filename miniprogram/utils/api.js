// utils/api.js
// 后端接口封装：支持云托管调用 + 本地开发 wx.request
const config = require('./config')

// 本地开发时使用的稳定 openid（云托管环境下会被 X-WX-OPENID 覆盖，无副作用）
const LOCAL_OPENID_KEY = 'mxlm_local_openid'
function getLocalOpenid() {
  let oid = wx.getStorageSync(LOCAL_OPENID_KEY)
  if (!oid) {
    oid = 'local-' + Date.now() + '-' + Math.floor(Math.random() * 100000)
    wx.setStorageSync(LOCAL_OPENID_KEY, oid)
  }
  return oid
}

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
          const err = new Error((body && body.message) || '接口异常')
          err.code = body && body.code
          reject(err)
        }
      } else {
        reject(new Error('网络异常，状态码 ' + res.statusCode))
      }
    }
    const failHandler = (err) => {
      reject(new Error(err.errMsg || '请求失败'))
    }

    // 统一请求头（本地开发时用 X-Openid 兜底，云托管自动带 X-WX-OPENID）
    const commonHeader = {
      'content-type': 'application/json',
      'X-Openid': getLocalOpenid()
    }

    if (config.useCloudContainer) {
      // 生产：微信云托管调用（自动带 openid，无需配业务域名）
      wx.cloud.callContainer({
        config: { env: config.cloudEnv },
        path: url,
        method,
        data,
        header: Object.assign({ 'X-WX-SERVICE': config.cloudService }, commonHeader),
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
        header: commonHeader,
        success: successHandler,
        fail: failHandler
      })
    }
  })
}

module.exports = {
  // ---------- 原有 ----------
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

  // ---------- 用户体系新增 ----------
  getQuota() {
    return request('/api/roast/quota', 'GET')
  },
  getUserStats() {
    return request('/api/user/stats', 'GET')
  },
  listHistory(page = 1, size = 20) {
    return request(`/api/history?page=${page}&size=${size}`, 'GET')
  },
  deleteHistory(roastId) {
    return request(`/api/history/${roastId}`, 'DELETE')
  },
  addFavorite(roastId) {
    return request(`/api/favorite/${roastId}`, 'POST')
  },
  removeFavorite(roastId) {
    return request(`/api/favorite/${roastId}`, 'DELETE')
  },
  listFavorites(page = 1, size = 20) {
    return request(`/api/favorites?page=${page}&size=${size}`, 'GET')
  },

  /**
   * 卡片埋点上报（save / share）。
   * 静默失败：网络异常或后端报错都会被吞掉，绝不阻塞用户主流程。
   * generate 事件后端自动埋，无需前端调用。
   */
  trackCardEvent(roastId, template, event) {
    if (!template || !event) return Promise.resolve()
    return request('/api/track/card', 'POST', { roastId, template, event })
      .catch(() => {}) // 埋点失败静默降级
  },

  /**
   * 拼接完整图片 URL
   * 云托管模式下图片走 <cloudEnv>-<cloudService> 的网关或需要单独 CDN；
   * MVP 阶段先直接使用云托管的公网访问域名（在 config.imageBaseUrl 里配）
   */
  fullImageUrl(path) {
    if (!path) return ''
    if (path.startsWith('http')) return path
    return (config.imageBaseUrl || config.apiBaseUrl) + path
  }
}

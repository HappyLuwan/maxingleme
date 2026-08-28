// app.js
const config = require('./utils/config')

// 隐私政策版本号：每次隐私政策有实质变更时递增，触发用户重新同意
const PRIVACY_VERSION = 1

App({
  onLaunch() {
    // 初始化云能力（云托管调用依赖）
    if (!wx.cloud) {
      console.error('当前微信版本过低，无法使用云能力，请升级到 2.2.3 以上')
    } else {
      wx.cloud.init({
        env: config.cloudEnv,
        traceUser: true
      })
    }

    // 本地日志
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 首次启动或隐私政策更新后，弹窗要求用户同意
    this.checkPrivacyAgreement()
  },

  /**
   * 隐私政策同意检查：
   * - 已同意且版本一致 → 直接放行
   * - 未同意或版本变更 → 弹 modal，同意后写 storage；拒绝则退出小程序
   */
  checkPrivacyAgreement() {
    const agreed = wx.getStorageSync('privacyAgreedVersion')
    if (agreed === PRIVACY_VERSION) return

    wx.showModal({
      title: '欢迎使用「骂醒了么」',
      content:
        '在使用本小程序前，请阅读并同意《用户服务协议》和《隐私政策》。\n\n' +
        '我们会保存你的困扰文本 90 天用于历史回顾，你可随时在"我的"页面长按删除。',
      confirmText: '同意并使用',
      cancelText: '查看协议',
      confirmColor: '#ff5252',
      success: (res) => {
        if (res.confirm) {
          wx.setStorageSync('privacyAgreedVersion', PRIVACY_VERSION)
          wx.setStorageSync('privacyAgreedAt', Date.now())
        } else {
          // 点"查看协议"：跳到隐私政策页；用户看完回来后再次弹窗
          wx.navigateTo({
            url: '/pages/privacy/privacy',
            fail: () => {
              // 如果当前页面不允许 navigateTo，改用 switch tab 后再 navigate
              // 静默失败
            }
          })
        }
      }
    })
  },

  globalData: {
    userInfo: null,
    privacyVersion: PRIVACY_VERSION
  }
})

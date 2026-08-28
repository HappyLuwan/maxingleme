// pages/about/about.js
Page({
  data: {
    version: '1.0.0',
    // ICP 备案号（已备案）
    icpNo: '陕ICP备2026023416号-1X',
    hasIcp: true
  },

  onLoad() {},

  onNavAgreement() {
    wx.navigateTo({ url: '/pages/agreement/agreement' })
  },

  onNavPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' })
  },

  onFeedback() {
    wx.showModal({
      title: '意见反馈',
      content: '请在小程序内长按【骂醒了么】客服按钮，或联系开发者微信\n\n如需删除你的历史数据，请通过客服提交。',
      showCancel: false,
      confirmText: '知道了'
    })
  },

  onCopy(e) {
    const text = e.currentTarget.dataset.text || ''
    if (!text) return
    wx.setClipboardData({
      data: text,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' })
      }
    })
  }
})

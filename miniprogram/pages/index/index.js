// pages/index/index.js
const api = require('../../utils/api')

Page({
  data: {
    userInput: '',
    canSubmit: false,
    styles: [],
    selectedStyle: 'yiju',
    loading: false,
    loadingTip: '正在骂醒你...',
    examples: [
      '前任又来找我了，我心动了怎么办',
      '想剥手买 3000 块的包，但这个月工资才 5000',
      '论文还没开题就想摆烂了',
      '凌晨 2 点还在刷手机，明天又要迟到',
      '想吃夜宵了，就一口不算破戒吧？',
      '又加班到 10 点，感觉自己在为爱发电'
    ]
  },

  onLoad() {
    this.loadStyles()
  },

  /**
   * 拉取风格列表
   */
  loadStyles() {
    api.listStyles().then((list) => {
      this.setData({ styles: list })
    }).catch((err) => {
      console.error('加载风格失败', err)
      // 兼底：本地静态列表
      this.setData({
        styles: [
          { key: 'yiju', name: '一针见血', emoji: '💥', description: '一句话骂醒，字字暴击', enabled: true },
          { key: 'yinyang', name: '阴阳怪气', emoji: '😏', description: '阴阳怪气小天才', enabled: true },
          { key: 'wenrou', name: '温柔姐姐', emoji: '🌸', description: '温柔知性，直击心底', enabled: true },
          { key: 'luxun', name: '鲁迅式', emoji: '📜', description: '深刻犀利，字字诛心', enabled: true },
          { key: 'zhexue', name: '哲学家', emoji: '🌙', description: '从哲学高度让你顿悟', enabled: true },
          { key: 'custom', name: '自定义', emoji: '✍️', description: '输入什么，卡片就是什么', enabled: true }
        ]
      })
    })
  },

  /**
   * 输入内容
   */
  onInput(e) {
    const val = e.detail.value || ''
    this.setData({
      userInput: val,
      canSubmit: val.trim().length > 0
    })
  },

  /**
   * 选择风格
   */
  onSelectStyle(e) {
    const key = e.currentTarget.dataset.key
    const style = this.data.styles.find(s => s.key === key)
    if (!style || !style.enabled) {
      wx.showToast({ title: '该风格敬请期待～', icon: 'none' })
      return
    }
    this.setData({ selectedStyle: key })
    wx.vibrateShort({ type: 'light' })
  },

  /**
   * 示例点击自动填入
   */
  onExampleTap(e) {
    const text = e.currentTarget.dataset.text || ''
    this.setData({
      userInput: text,
      canSubmit: text.trim().length > 0
    })
    wx.vibrateShort({ type: 'light' })
  },

  /**
   * 一键骂醒
   */
  onRoast() {
    const input = this.data.userInput.trim()
    if (!input) {
      wx.showToast({ title: '先告诉我你的烦恼吧', icon: 'none' })
      return
    }
    // 随机 loading 文案，避免单一
    const loadingTips = [
      '正在骂醒你...',
      'AI 正在醍酿一记暴击...',
      '深呼吸，马上骂到...',
      '正在挑选骂你的角度...',
      '醒醒醒，马上到...'
    ]
    const tip = loadingTips[Math.floor(Math.random() * loadingTips.length)]
    this.setData({ loading: true, loadingTip: tip })

    api.roast(input, this.data.selectedStyle).then((result) => {
      this.setData({ loading: false })
      // 跳转到结果页，携带数据
      wx.setStorageSync('lastRoast', result)
      wx.navigateTo({
        url: '/pages/result/result?roastId=' + result.roastId
      })
    }).catch((err) => {
      this.setData({ loading: false })
      wx.showModal({
        title: '骂不动了',
        content: err.message || '请稍后再试',
        showCancel: false
      })
    })
  },

  /**
   * 首页分享
   */
  onShareAppMessage() {
    return {
      title: '🔥 骂醒了么 - 让 AI 一句话骂醒你',
      path: '/pages/index/index',
      imageUrl: '' // 可放分享封面图
    }
  },

  onShareTimeline() {
    return {
      title: '🔥 骂醒了么 - 你的 AI 嘴替',
      query: ''
    }
  },

  /**
   * 页脚跳转 - 用户协议
   */
  onNavAgreement() {
    wx.navigateTo({ url: '/pages/agreement/agreement' })
  },

  /**
   * 页脚跳转 - 隐私政策
   */
  onNavPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' })
  },

  /**
   * 页脚跳转 - 关于（tabBar 页面用 switchTab）
   */
  onNavAbout() {
    wx.switchTab({ url: '/pages/about/about' })
  }
})

// pages/index/index.js
const api = require('../../utils/api')

Page({
  data: {
    userInput: '',
    styles: [],
    selectedStyle: 'dushe',
    loading: false,
    examples: [
      '前任又来找我了，我心动了怎么办',
      '想剁手买 3000 块的包，但这个月工资才 5000',
      '论文还没开题就想摆烂了',
      '凌晨 2 点还在刷手机，明天又要迟到',
      '想吃夜宵了，就一口不算破戒吧？',
      '领导又 PUA 我，我要不要辞职'
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
      // 兜底：本地静态列表
      this.setData({
        styles: [
          { key: 'dushe', name: '毒舌暴击', emoji: '🔥', description: '犀利如刀，一针见血', enabled: true },
          { key: 'dongbei', name: '东北大姐', emoji: '🌶️', description: '东北大姐附体', enabled: true },
          { key: 'wenrou', name: '温柔姐姐', emoji: '🌸', description: '温柔知性，直击心底', enabled: true }
        ]
      })
    })
  },

  /**
   * 输入内容
   */
  onInput(e) {
    this.setData({ userInput: e.detail.value })
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
    const text = e.currentTarget.dataset.text
    this.setData({ userInput: text })
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
    this.setData({ loading: true })

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
  }
})

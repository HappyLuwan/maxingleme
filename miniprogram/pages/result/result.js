// pages/result/result.js
const api = require('../../utils/api')

// 正式款：9 套卡片按吸引力排序（首屏展示前 3 张最抓眼）
// 顺序依据：视觉冲击 + 分享传播欲 + 辨识度 + 通用性 综合评估
const TEMPLATES = [
  { key: 'tarot',   name: '塔罗指引', icon: '🔮' },
  { key: 'rx',      name: '醒神药方', icon: '💊' },
  { key: 'wrapped', name: '年终盘点', icon: '🎯' },
  { key: 'checkin', name: '清醒打卡', icon: '📊' },
  { key: 'track',   name: '单曲循环', icon: '💿' },
  { key: 'news',    name: '社论快报', icon: '📰' },
  { key: 'chat',    name: '对话截屏', icon: '💬' },
  { key: 'comment', name: '树洞回响', icon: '🌙' },
  { key: 'note',    name: '便利贴纸', icon: '🗒' }
]

Page({
  data: {
    roast: {
      roastId: '',
      content: '',
      style: '',
      styleName: '',
      styleEmoji: ''
    },
    templates: TEMPLATES,
    selectedTemplate: '',      // 空表示未选，用户主动点后再生成，减少首屏等待
    generatingCard: false,
    cardImageUrl: '',
    isFavorite: false
  },

  onLoad(options) {
    // 从本地缓存拿骂醒数据（首页存的）
    const roast = wx.getStorageSync('lastRoast')
    if (roast && roast.roastId === options.roastId) {
      this.setData({ roast })
      // 注意：不再自动生成卡片，用户读完文案主动选风格再生成，避免首屏等待
      // 同时拉取收藏状态（不阻塞主流程）
      this.loadFavoriteStatus(options.roastId)
    } else {
      wx.showToast({ title: '数据丢失，请重新骂醒', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1500)
    }
  },

  /**
   * 拉取当前记录的收藏状态（从“我的”页进入的情况能看到正确标识）
   */
  loadFavoriteStatus(roastId) {
    // 尝试从历史接口中预先读取标识（历史列表已带 isFavorite）；
    // 简化起见，这里直接调列表接口滤一下（无专门 GET 单条 API，成本可接受）
    api.listFavorites(1, 100).then((res) => {
      const hit = (res.list || []).some((it) => it.roastId === roastId)
      this.setData({ isFavorite: hit })
    }).catch(() => {})
  },

  /**
   * 切换收藏状态
   */
  onToggleFavorite() {
    const roastId = this.data.roast.roastId
    if (!roastId) return
    const wasFav = this.data.isFavorite
    const call = wasFav ? api.removeFavorite : api.addFavorite
    call(roastId).then(() => {
      wx.vibrateShort({ type: 'light' })
      this.setData({ isFavorite: !wasFav })
      wx.showToast({
        title: wasFav ? '已取消收藏' : '已收藏',
        icon: 'success'
      })
    }).catch((err) => {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    })
  },

  /**
   * 选择卡片模板 —— 点击即生成，无需再点按钮
   */
  onSelectTemplate(e) {
    const key = e.currentTarget.dataset.key
    // 正在生成时忽略新的切换请求，避免并发覆盖
    if (this.data.generatingCard) {
      wx.showToast({ title: '生成中，请稍候', icon: 'none' })
      return
    }
    // 点了当前已经渲染成功的模板，不重复生成
    if (key === this.data.selectedTemplate && this.data.cardImageUrl) {
      return
    }
    this.setData({ selectedTemplate: key })
    wx.vibrateShort({ type: 'light' })
    // 立即触发生成
    this.onGenerateCard()
  },

  /**
   * 生成卡片
   */
  onGenerateCard() {
    if (!this.data.roast.roastId) {
      wx.showToast({ title: '骂醒记录已失效', icon: 'none' })
      return
    }
    this.setData({ generatingCard: true, cardImageUrl: '' })
    wx.showLoading({ title: '生成中...', mask: true })

    api.generateCard(this.data.roast.roastId, this.data.selectedTemplate).then((result) => {
      wx.hideLoading()
      // 优先用 Base64（云托管零配置就能看图），否则降级到 http URL
      const imgSrc = result.imageBase64 || api.fullImageUrl(result.imageUrl)
      this.setData({
        generatingCard: false,
        cardImageUrl: imgSrc
      })
      wx.vibrateShort({ type: 'medium' })
    }).catch((err) => {
      wx.hideLoading()
      this.setData({ generatingCard: false })
      wx.showModal({
        title: '生成失败',
        content: err.message || '请稍后重试',
        showCancel: false
      })
    })
  },

  /**
   * 保存图片到相册
   * - 如果是 dataURL（base64），先写到临时文件再保存
   * - 如果是 http URL，走 downloadFile
   */
  onSaveImage() {
    if (!this.data.cardImageUrl) return
    const src = this.data.cardImageUrl
    if (src.startsWith('data:image')) {
      this.saveBase64Image(src)
    } else {
      this.saveRemoteImage(src)
    }
  },

  saveBase64Image(dataUrl) {
    wx.showLoading({ title: '保存中...', mask: true })
    const base64 = dataUrl.replace(/^data:image\/\w+;base64,/, '')
    const filePath = `${wx.env.USER_DATA_PATH}/mxlm_card_${Date.now()}.png`
    const fs = wx.getFileSystemManager()
    fs.writeFile({
      filePath,
      data: base64,
      encoding: 'base64',
      success: () => {
        wx.saveImageToPhotosAlbum({
          filePath,
          success: () => {
            wx.hideLoading()
            wx.showToast({ title: '已保存到相册', icon: 'success' })
            // 埋点：保存成功后上报（静默失败）
            api.trackCardEvent(this.data.roast.roastId, this.data.selectedTemplate, 'save')
          },
          fail: (err) => {
            wx.hideLoading()
            if (err.errMsg.indexOf('auth deny') > -1 || err.errMsg.indexOf('authorize') > -1) {
              wx.showModal({
                title: '需要相册权限',
                content: '请在设置中开启保存到相册的权限',
                confirmText: '去设置',
                success: (m) => { if (m.confirm) wx.openSetting() }
              })
            } else {
              wx.showToast({ title: '保存失败', icon: 'none' })
            }
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '写入临时文件失败', icon: 'none' })
      }
    })
  },

  saveRemoteImage(url) {
    wx.showLoading({ title: '下载中...' })
    wx.downloadFile({
      url,
      success: (res) => {
        wx.hideLoading()
        if (res.statusCode !== 200) {
          wx.showToast({ title: '下载失败', icon: 'none' })
          return
        }
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            wx.showToast({ title: '已保存到相册', icon: 'success' })
            // 埋点：保存成功后上报（静默失败）
            api.trackCardEvent(this.data.roast.roastId, this.data.selectedTemplate, 'save')
          },
          fail: (err) => {
            if (err.errMsg.indexOf('auth deny') > -1 || err.errMsg.indexOf('authorize') > -1) {
              wx.showModal({
                title: '需要相册权限',
                content: '请在设置中开启保存到相册的权限',
                confirmText: '去设置',
                success: (m) => { if (m.confirm) wx.openSetting() }
              })
            } else {
              wx.showToast({ title: '保存失败', icon: 'none' })
            }
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '下载失败', icon: 'none' })
      }
    })
  },

  /**
   * 再骂一次
   */
  onAgain() {
    wx.navigateBack()
  },

  /**
   * 分享给朋友（带卡片图作为封面）
   * 注：wx.onShareAppMessage.imageUrl 不支持 base64，如果是 base64 则不传 imageUrl，由微信默认截页面
   */
  onShareAppMessage() {
    const src = this.data.cardImageUrl
    const isHttp = src && src.startsWith('http')
    // 埋点：分享事件（wx 无法区分真实发送，只能捕获点击分享）
    if (this.data.roast.roastId && this.data.selectedTemplate) {
      api.trackCardEvent(this.data.roast.roastId, this.data.selectedTemplate, 'share')
    }
    return {
      title: '今日金句：' + this.truncate(this.data.roast.content, 30) + ' —— 骂醒了么',
      path: '/pages/index/index',
      imageUrl: isHttp ? src : ''
    }
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline() {
    const src = this.data.cardImageUrl
    const isHttp = src && src.startsWith('http')
    // 埋点：分享朋友圈也计一次 share
    if (this.data.roast.roastId && this.data.selectedTemplate) {
      api.trackCardEvent(this.data.roast.roastId, this.data.selectedTemplate, 'share')
    }
    return {
      title: this.truncate(this.data.roast.content, 30) + ' —— 骂醒了么',
      query: '',
      imageUrl: isHttp ? src : ''
    }
  },

  truncate(str, len) {
    if (!str) return ''
    return str.length > len ? str.substring(0, len) + '...' : str
  }
})

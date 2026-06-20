export const indoorNodes = [
  {
    id: 'gate',
    name: '教学楼入口',
    type: 'entrance',
    x: 70,
    y: 260,
    detail: '从教学楼正门进入后，面向中庭和主走廊。',
  },
  {
    id: 'lobby',
    name: '一层中庭',
    type: 'hall',
    x: 190,
    y: 260,
    detail: '中庭是室内导航的核心交汇点，可前往教室区、楼梯、电梯和服务设施。',
  },
  {
    id: 'stairs-west',
    name: '西侧楼梯',
    type: 'stairs',
    x: 190,
    y: 125,
    detail: '西侧楼梯靠近入口，适合前往上课教室或快速疏散。',
  },
  {
    id: 'vending',
    name: '自动售卖机',
    type: 'service',
    x: 340,
    y: 125,
    detail: '自动售卖机位于北侧走廊中段，可购买饮料、矿泉水和简单零食。',
  },
  {
    id: 'water',
    name: '饮水机',
    type: 'service',
    x: 510,
    y: 125,
    detail: '饮水机靠近自习区，提供热水和常温水。',
  },
  {
    id: 'study',
    name: '开放自习区',
    type: 'study',
    x: 650,
    y: 125,
    detail: '开放自习区适合课间短时学习，靠近饮水机和东侧楼梯。',
  },
  {
    id: 'class-a',
    name: '101 教室',
    type: 'classroom',
    x: 340,
    y: 260,
    detail: '101 教室位于主走廊中段，适合从入口经中庭直行到达。',
  },
  {
    id: 'class-b',
    name: '102 教室',
    type: 'classroom',
    x: 510,
    y: 260,
    detail: '102 教室靠近电梯和教务办公室。',
  },
  {
    id: 'elevator',
    name: '电梯',
    type: 'elevator',
    x: 650,
    y: 260,
    detail: '电梯位于东侧竖向交通区，适合携带设备或行动不便时使用。',
  },
  {
    id: 'office',
    name: '教务办公室',
    type: 'office',
    x: 510,
    y: 395,
    detail: '教务办公室可咨询课表、教室借用、考试安排等事项。',
  },
  {
    id: 'toilet',
    name: '卫生间',
    type: 'toilet',
    x: 650,
    y: 395,
    detail: '卫生间位于东南角，靠近电梯和东侧楼梯。',
  },
  {
    id: 'stairs-east',
    name: '东侧楼梯',
    type: 'stairs',
    x: 780,
    y: 395,
    detail: '东侧楼梯靠近卫生间和电梯，可作为疏散出口。',
  },
]

export const indoorEdges = [
  { u: 'gate', v: 'lobby', distance: 18 },
  { u: 'lobby', v: 'stairs-west', distance: 16 },
  { u: 'stairs-west', v: 'vending', distance: 22 },
  { u: 'vending', v: 'water', distance: 24 },
  { u: 'water', v: 'study', distance: 20 },
  { u: 'lobby', v: 'class-a', distance: 24 },
  { u: 'class-a', v: 'class-b', distance: 24 },
  { u: 'class-b', v: 'elevator', distance: 20 },
  { u: 'class-b', v: 'office', distance: 18 },
  { u: 'office', v: 'toilet', distance: 19 },
  { u: 'toilet', v: 'stairs-east', distance: 16 },
  { u: 'elevator', v: 'toilet', distance: 18 },
  { u: 'study', v: 'elevator', distance: 18 },
]

export const indoorTypeLabels = {
  entrance: '入口',
  hall: '中庭',
  stairs: '楼梯',
  service: '服务设施',
  study: '学习区',
  classroom: '教室',
  elevator: '电梯',
  office: '办公室',
  toilet: '卫生间',
}

export function buildIndoorInstruction(from, to) {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const horizontal = Math.abs(dx) > 18 ? (dx > 0 ? '向东' : '向西') : ''
  const vertical = Math.abs(dy) > 18 ? (dy > 0 ? '向南' : '向北') : ''
  const direction = [horizontal, vertical].filter(Boolean).join('再') || '直行'
  return `从${from.name}${direction}前往${to.name}`
}

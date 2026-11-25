        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "两条曲线的分歧补测",
  "module": "补测领片",
  "caption": "补测候选与领片",
  "detail": "同一弯模下，候选炉温、片厚与目标弯度须同时落在两条最新签注曲线的训练范围内并均可复算，按两条预测的分歧自高到低排序；两人各领剩余最靠前的工况，重试不重复领片。",
  "path": "/supplements",
  "columns": [
    {
      "name": "rank",
      "label": "名次"
    },
    {
      "name": "code",
      "label": "候选工况"
    },
    {
      "name": "jig",
      "label": "弯模"
    },
    {
      "name": "heat",
      "label": "保温温度 °C"
    },
    {
      "name": "thick",
      "label": "片厚 mm"
    },
    {
      "name": "target",
      "label": "目标弯度 mm"
    },
    {
      "name": "profile_a",
      "label": "最新曲线"
    },
    {
      "name": "prediction_a",
      "label": "最新预测 mm"
    },
    {
      "name": "profile_b",
      "label": "次新曲线"
    },
    {
      "name": "prediction_b",
      "label": "次新预测 mm"
    },
    {
      "name": "divergence",
      "label": "曲线分歧 mm"
    },
    {
      "name": "status",
      "label": "状态"
    },
    {
      "name": "claimed_by",
      "label": "领取人"
    },
    {
      "name": "coupon",
      "label": "补测试片"
    }
  ],
  "layout": "split",
  "view": "table",
  "actions": [
    {
      "name": "register_candidate",
      "label": "填报候选工况",
      "path": "/supplements/register-candidate",
      "fields": [
        {
          "name": "code",
          "label": "候选编号",
          "kind": "text",
          "initial": "C-04"
        },
        {
          "name": "jig",
          "label": "弯模编号",
          "kind": "text",
          "initial": "CL-44"
        },
        {
          "name": "heat",
          "label": "候选炉温 °C",
          "kind": "float",
          "initial": 500
        },
        {
          "name": "thick",
          "label": "片厚 mm",
          "kind": "float",
          "initial": 3
        },
        {
          "name": "target",
          "label": "目标弯度 mm",
          "kind": "float",
          "initial": 10
        }
      ],
      "help": "两条曲线都能复算且工况在各自训练范围内才参与排序；同一工况重复填报不重复建账。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已登记候选"
    },
    {
      "name": "claim",
      "label": "领取最靠前工况",
      "path": "/supplements/claim",
      "fields": [],
      "help": "领取剩余名次最靠前的工况并自动建立补测试片；手上未见证的片未交回前，重试只返回同一片，不会重复领片。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已领片"
    },
    {
      "name": "record_reading",
      "label": "登记一次冷却读数",
      "path": "/supplements/record-reading",
      "fields": [
        {
          "name": "candidate",
          "label": "候选工况编号",
          "kind": "text",
          "initial": "C-02"
        },
        {
          "name": "measured",
          "label": "冷却弯度 mm",
          "kind": "float",
          "initial": 8.4
        }
      ],
      "help": "每张补测片只允许登记一次冷却读数，登记后不可改写。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已登记读数"
    },
    {
      "name": "witness",
      "label": "见证纳入拟合",
      "path": "/supplements/witness",
      "fields": [
        {
          "name": "candidate",
          "label": "候选工况编号",
          "kind": "text",
          "initial": "C-02"
        }
      ],
      "help": "复核见证后补测片才锁定进入训练账，参与后续曲线拟合。",
      "roles": [
        "reviewer"
      ],
      "success": "已见证"
    }
  ]
};

        export const {title} = page;
        export const key = "supplements";
        export async function render(root, role) {
          await workspace(root, role, page);

        }

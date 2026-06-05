# assets

`assets` is a namespace that groups named resources by category.

## Available Namespaces

### `assets.colors`

Named ASS colors grouped by shade.

```ass
{\1c!assets.colors.red[500]!}
```

Available color names:

`slate`, `gray`, `zinc`, `neutral`, `stone`, `red`, `orange`, `amber`,
`yellow`, `lime`, `green`, `emerald`, `teal`, `cyan`, `sky`, `blue`,
`indigo`, `violet`, `purple`, `fuchsia`, `pink`, `rose`.

Available shades:

`50`, `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`, `950`.

### `assets.shapes`

Named ASS drawing strings that can be used in `\p` drawings or passed to
shape helpers.

```ass
{\p1}!assets.shapes.star!{\p0}
```

```ass
{\p1}!shape.rotate(assets.shapes.star, 25)!{\p0}
```

#### Shape gallery

**Basic**

<table><tr>
<td align="center"><img src="shapes/circle.png" width="80"/><br/><code>circle</code></td>
<td align="center"><img src="shapes/triangle.png" width="80"/><br/><code>triangle</code></td>
<td align="center"><img src="shapes/rectangle.png" width="80"/><br/><code>rectangle</code></td>
<td align="center"><img src="shapes/circangle.png" width="80"/><br/><code>circangle</code></td>
<td align="center"><img src="shapes/pentagon.png" width="80"/><br/><code>pentagon</code></td>
<td align="center"><img src="shapes/hexagon.png" width="80"/><br/><code>hexagon</code></td>
<td align="center"><img src="shapes/octagon.png" width="80"/><br/><code>octagon</code></td>
<td align="center"><img src="shapes/diamond.png" width="80"/><br/><code>diamond</code></td>
</tr><tr>
<td align="center"><img src="shapes/pixel.png" width="80"/><br/><code>pixel</code></td>
<td align="center"><img src="shapes/gear.png" width="80"/><br/><code>gear</code></td>
<td align="center"><img src="shapes/bubble.png" width="80"/><br/><code>bubble</code></td>
<td align="center"><img src="shapes/trebol.png" width="80"/><br/><code>trebol</code></td>
</tr></table>

**Hearts**

<table><tr>
<td align="center"><img src="shapes/heart.png" width="80"/><br/><code>heart</code></td>
<td align="center"><img src="shapes/heart2t.png" width="80"/><br/><code>heart2t</code></td>
<td align="center"><img src="shapes/heart_b.png" width="80"/><br/><code>heart_b</code></td>
</tr></table>

**Shines**

<table><tr>
<td align="center"><img src="shapes/shine1t.png" width="80"/><br/><code>shine1t</code></td>
<td align="center"><img src="shapes/shine2t.png" width="80"/><br/><code>shine2t</code></td>
<td align="center"><img src="shapes/shine3t.png" width="80"/><br/><code>shine3t</code></td>
<td align="center"><img src="shapes/shine4t.png" width="80"/><br/><code>shine4t</code></td>
</tr></table>

**Feathers**

<table><tr>
<td align="center"><img src="shapes/feather.png" width="80"/><br/><code>feather</code></td>
<td align="center"><img src="shapes/feather2.png" width="80"/><br/><code>feather2</code></td>
</tr></table>

**Music notes**

<table><tr>
<td align="center"><img src="shapes/note1t.png" width="80"/><br/><code>note1t</code></td>
<td align="center"><img src="shapes/note2t.png" width="80"/><br/><code>note2t</code></td>
<td align="center"><img src="shapes/note3t.png" width="80"/><br/><code>note3t</code></td>
<td align="center"><img src="shapes/note4t.png" width="80"/><br/><code>note4t</code></td>
</tr></table>

**Stars**

<table><tr>
<td align="center"><img src="shapes/star.png" width="80"/><br/><code>star</code></td>
<td align="center"><img src="shapes/star1t.png" width="80"/><br/><code>star1t</code></td>
<td align="center"><img src="shapes/star2t.png" width="80"/><br/><code>star2t</code></td>
<td align="center"><img src="shapes/star3t.png" width="80"/><br/><code>star3t</code></td>
<td align="center"><img src="shapes/star4t.png" width="80"/><br/><code>star4t</code></td>
<td align="center"><img src="shapes/star5t.png" width="80"/><br/><code>star5t</code></td>
<td align="center"><img src="shapes/star6t.png" width="80"/><br/><code>star6t</code></td>
<td align="center"><img src="shapes/star7t.png" width="80"/><br/><code>star7t</code></td>
</tr><tr>
<td align="center"><img src="shapes/star8t.png" width="80"/><br/><code>star8t</code></td>
<td align="center"><img src="shapes/star9t.png" width="80"/><br/><code>star9t</code></td>
<td align="center"><img src="shapes/star10t.png" width="80"/><br/><code>star10t</code></td>
</tr></table>

**Sakura**

<table><tr>
<td align="center"><img src="shapes/sakura.png" width="80"/><br/><code>sakura</code></td>
<td align="center"><img src="shapes/sakura1t.png" width="80"/><br/><code>sakura1t</code></td>
<td align="center"><img src="shapes/sakura2t.png" width="80"/><br/><code>sakura2t</code></td>
<td align="center"><img src="shapes/sakura3t.png" width="80"/><br/><code>sakura3t</code></td>
<td align="center"><img src="shapes/sakura4t.png" width="80"/><br/><code>sakura4t</code></td>
<td align="center"><img src="shapes/sakura5t.png" width="80"/><br/><code>sakura5t</code></td>
<td align="center"><img src="shapes/sakura6t.png" width="80"/><br/><code>sakura6t</code></td>
<td align="center"><img src="shapes/sakura7t.png" width="80"/><br/><code>sakura7t</code></td>
</tr></table>

**Snow**

<table><tr>
<td align="center"><img src="shapes/snow1t.png" width="80"/><br/><code>snow1t</code></td>
<td align="center"><img src="shapes/snow2t.png" width="80"/><br/><code>snow2t</code></td>
<td align="center"><img src="shapes/snow3t.png" width="80"/><br/><code>snow3t</code></td>
</tr></table>

**Flowers**

<table><tr>
<td align="center"><img src="shapes/flower1t.png" width="80"/><br/><code>flower1t</code></td>
<td align="center"><img src="shapes/flower2t.png" width="80"/><br/><code>flower2t</code></td>
<td align="center"><img src="shapes/flower3t.png" width="80"/><br/><code>flower3t</code></td>
<td align="center"><img src="shapes/flower4t.png" width="80"/><br/><code>flower4t</code></td>
<td align="center"><img src="shapes/flower5t.png" width="80"/><br/><code>flower5t</code></td>
<td align="center"><img src="shapes/flower6t.png" width="80"/><br/><code>flower6t</code></td>
<td align="center"><img src="shapes/flower7t.png" width="80"/><br/><code>flower7t</code></td>
<td align="center"><img src="shapes/flower8t.png" width="80"/><br/><code>flower8t</code></td>
</tr><tr>
<td align="center"><img src="shapes/flower9t.png" width="80"/><br/><code>flower9t</code></td>
<td align="center"><img src="shapes/flower10t.png" width="80"/><br/><code>flower10t</code></td>
<td align="center"><img src="shapes/flower11t.png" width="80"/><br/><code>flower11t</code></td>
<td align="center"><img src="shapes/flower12t.png" width="80"/><br/><code>flower12t</code></td>
<td align="center"><img src="shapes/flower13t.png" width="80"/><br/><code>flower13t</code></td>
<td align="center"><img src="shapes/flower14t.png" width="80"/><br/><code>flower14t</code></td>
<td align="center"><img src="shapes/flower15t.png" width="80"/><br/><code>flower15t</code></td>
<td align="center"><img src="shapes/flower16t.png" width="80"/><br/><code>flower16t</code></td>
</tr><tr>
<td align="center"><img src="shapes/flower17t.png" width="80"/><br/><code>flower17t</code></td>
<td align="center"><img src="shapes/flower18t.png" width="80"/><br/><code>flower18t</code></td>
<td align="center"><img src="shapes/flower19t.png" width="80"/><br/><code>flower19t</code></td>
<td align="center"><img src="shapes/flower20t.png" width="80"/><br/><code>flower20t</code></td>
<td align="center"><img src="shapes/flower21t.png" width="80"/><br/><code>flower21t</code></td>
<td align="center"><img src="shapes/flower22t.png" width="80"/><br/><code>flower22t</code></td>
<td align="center"><img src="shapes/flower23t.png" width="80"/><br/><code>flower23t</code></td>
<td align="center"><img src="shapes/flower24t.png" width="80"/><br/><code>flower24t</code></td>
</tr><tr>
<td align="center"><img src="shapes/flower25t.png" width="80"/><br/><code>flower25t</code></td>
<td align="center"><img src="shapes/flower26t.png" width="80"/><br/><code>flower26t</code></td>
<td align="center"><img src="shapes/flower27t.png" width="80"/><br/><code>flower27t</code></td>
<td align="center"><img src="shapes/flower28t.png" width="80"/><br/><code>flower28t</code></td>
<td align="center"><img src="shapes/flower29t.png" width="80"/><br/><code>flower29t</code></td>
</tr></table>

**Geometric / abstract**

<table><tr>
<td align="center"><img src="shapes/cristal17.png" width="80"/><br/><code>cristal17</code></td>
<td align="center"><img src="shapes/geometric10.png" width="80"/><br/><code>geometric10</code></td>
<td align="center"><img src="shapes/diagonal13r.png" width="80"/><br/><code>diagonal13r</code></td>
<td align="center"><img src="shapes/diagonal13l.png" width="80"/><br/><code>diagonal13l</code></td>
</tr></table>

Use [`shape`](./shape.md) for geometry operations on drawing strings.

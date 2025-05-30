import math
import os
import random
import sys  
import time

import pygame as pg

WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
BEAM_INTERVAL = 25
NEOBEAM_NUM = 16
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    return x_diff / norm, y_diff / norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """

    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.last_shot = -BEAM_INTERVAL
        self.state = "normal"
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        if self.state == "hyper":  #ハイパーの分岐
            self.hyper_life -= 1  #時間制限
            if self.hyper_life < 0:
                self.state = "normal"
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed * sum_mv[0], self.speed * sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed * sum_mv[0], -self.speed * sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if self.state == "hyper":  #ハイパーになったときにラプラシアンフィルタ
            self.image = pg.transform.laplacian(self.image)
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """

    colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
    ]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2 * rad, 2 * rad))
        color = random.choice(
            __class__.colors
        )  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery + emy.rect.height // 2
        self.speed = 6
        self.state = "active"
    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """

    def __init__(self, bird: Bird, tmr: int):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10
        self.angle0 = 0

        bird.last_shot = tmr

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam(pg.sprite.Sprite):
    """
    ネオビームに関するクラス
    """

    def __init__(self, bird: Bird, num: int):
        super().__init__()
        self.bird = bird
        self.num = num

    def gen_beams(self, tmr: int) -> list[Beam]:
        """
        ビームを生成する
        360度をself.numで割った角度でビームを放つ
        """
        beams = []
        for i in range(self.num):
            angle = 360 / self.num * i
            vx = math.cos(math.radians(angle))
            vy = -math.sin(math.radians(angle))

            beam = Beam(self.bird, tmr)
            beam.vx, beam.vy = vx, vy
            beam.image = pg.transform.rotozoom(
                pg.image.load(f"fig/beam.png"), angle, 1.0
            )
            beam.rect.centery = self.bird.rect.centery + self.bird.rect.height * vy
            beam.rect.centerx = self.bird.rect.centerx + self.bird.rect.width * vx

            beams.append(beam)

        return beams


class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス
    """
    def __init__(self, bird: Bird, life: int):
        """
        防御壁Surfaceを生成する
        引数1 bird：防御するこうかとん
        引数2 life：発動時間
        """
        super().__init__()
        self.bird = bird
        self.life = life
        self.width = 20  # 防御壁の幅
        self.height = bird.rect.height * 2  # こうかとんの身長の2倍
        self.image = pg.Surface((self.width, self.height))
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, self.width, self.height))
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.update_position()

    def update_position(self):
        """
        こうかとんの向きに応じて防御壁の位置と角度を更新する
        """
        vx, vy = self.bird.dire
        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pg.Surface((self.width, self.height))
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, self.width, self.height))
        self.image.set_colorkey((0, 0, 0))
        self.image = pg.transform.rotozoom(self.image, angle, 1.0)
        self.image.set_colorkey((0, 0, 0))  # 回転後も透明化を適用
        self.rect = self.image.get_rect()
        self.rect.center = (
            self.bird.rect.centerx + math.cos(math.radians(angle)) * self.bird.rect.width,
            self.bird.rect.centery - math.sin(math.radians(angle)) * self.bird.rect.height
        )

    def update(self):
        """
        発動時間を1減算し、こうかとんの向きに応じて位置を更新する
        発動時間が0未満になったら、防御壁を消去する
        """
        self.life -= 1
        self.update_position()
        if self.life < 0:
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """

    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life // 10 % 2]
        if self.life < 0:
            self.kill()


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """

    def __init__(self, life: int):
        """
        重力場を発生させる背景を生成する
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.rect = self.image.get_rect()
        self.image.set_alpha(128)
        self.life = life

    def update(self):
        """
        発動させるときにライフを1減算する
        ライフが0以下なら死ぬ
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """

    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT // 2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """

    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT - 50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP(pg.sprite.Sprite):
    """
    EMP（電磁パルス）に関するクラス
    スコア20以上で'e'を押すと発動
    
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group):
        super().__init__()
        self.life = 3
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.Enemy = emys
        self.Bomb = bombs
        self.screen = pg.Surface


        for emy in emys:
            emy.interval = math.inf  # 爆弾投下できなくなる
            emy.image = pg.transform.laplacian(emy.image)  # ラプラシアンフィルタ

        for bomb in bombs:
            bomb.speed *= 0.5
            bomb.state = "inactive"


        # 背景
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (244, 229, 17), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()


    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()

        





def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    grav = pg.sprite.Group()
    emps = pg.sprite.Group()
    shields = pg.sprite.Group()  # 防御壁グループを追加

    tmr = 0
    life = 400
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()

        if tmr - bird.last_shot > BEAM_INTERVAL:
            if key_lst[pg.K_SPACE] == 1 and key_lst[pg.K_LSHIFT] == 1:
                neo_beam = NeoBeam(bird, NEOBEAM_NUM)
                beams.add(neo_beam.gen_beams(tmr))
            elif key_lst[pg.K_SPACE] == 1:
                beams.add(Beam(bird, tmr))

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value >= 200:
                    score.value -= 200
                    grav.add(Gravity(life))
            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT:  #無敵発動
                if score.value >= 100:
                    score.value -= 100
                    bird.state = "hyper"
                    bird.hyper_life = 500
                    bird.update(key_lst, screen)  #見た目変更のためにアップデート
            if event.type == pg.KEYDOWN and event.key == pg.K_e and score.value > 20:
                emps.add(EMP(emys, bombs))
                score.value -= 20
            if event.type == pg.KEYDOWN and event.key == pg.K_s:
                # 防御壁発動条件：sキー押下、スコアが50以上、他の防御壁が存在しない
                if score.value >= 50 and len(shields) == 0:
                    shields.add(Shield(bird, 400))  # 防御壁を追加（発動時間400フレーム）
                    score.value -= 50  # 防御壁発動のためにスコアを消費
        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(
            emys, beams, True, True
        ).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(
            bombs, beams, True, True
        ).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # 防御壁と爆弾の衝突判定
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bird.state == "normal":  #通常時処理
                if bomb.state != "inactive":
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    return
            elif bird.state == "hyper":  #ハイパー時の無敵処理
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1  # 1点アップ
                bomb.kill()

        for emy in pg.sprite.groupcollide(
            emys, grav, True, False
        ).keys():  # 重力場を使って倒した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(
            bombs, grav, True, False
        ).keys():  # 重力場を使って倒した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        grav.update()
        grav.draw(screen)
        bombs.update()
        bombs.draw(screen)
        shields.update()  # 防御壁の更新
        shields.draw(screen)  # 防御壁の描画
        exps.update()
        exps.draw(screen)
        score.update(screen)

        emps.update()
        emps.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()

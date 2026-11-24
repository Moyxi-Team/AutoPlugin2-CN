--[[ 
	Autoinstall plugin

	Licensed by Creative Commons Attribution-ShareAlike 4.0
	http://creativecommons.org/licenses/by-sa/4.0/
	
	Dev: TheHeroeGAC
	Designed By Gdljjrod & DevDavisNunez.
	Collaborators: BaltazaR4 & Wzjk.
]]

--Activamos Paleta de Colores Precargados
color.loadpalette()

snd = sound.load("ux0:data/AUTOPLUGIN2/bg/bg.mp3",1) or sound.load("ux0:data/AUTOPLUGIN2/bg/bg.ogg")
splash.zoom("imgs/splash.png")

--Imagen de Fondo
back = image.load("imgs/back1.png")
back2 = image.load("imgs/back2.png")


--==== [CN-MIRROR-HOOK v2] 国内镜像自愈层：官方在线更新覆盖脚本后依然生效 ====
if not __CN_MIRROR_HOOK then
	__CN_MIRROR_HOOK = true
	local __MIRROR = "https://gh-proxy.com/"
	local __PFX = {
		"https://raw.githubusercontent.com/",
		"https://github.com/",
		"https://api.github.com/",
		"https://objects.githubusercontent.com/",
		"https://codeload.github.com/",
	}
	local function __cn_mirror_url(u)
		if type(u) ~= "string" then return u end
		if string.sub(u, 1, #__MIRROR) == __MIRROR then return u end
		for i = 1, #__PFX do
			local p = __PFX[i]
			if string.sub(u, 1, #p) == p then return __MIRROR .. u end
		end
		return u
	end
	pcall(function()
		if type(http) == "table" then
			local _hget, _hdl = http.get, http.download
			if _hget then http.get = function(u, ...) return _hget(__cn_mirror_url(u), ...) end end
			if _hdl then http.download = function(u, ...) return _hdl(__cn_mirror_url(u), ...) end end
		end
	end)
end
--==== [/CN-MIRROR-HOOK v2] ====

dofile("git/shared.lua")
PLUGINS_PORT = channel.new("PLUGINS_PORT")
cont_global = atomic.new(0)
PLUGINS_PORT:push(cont_global)
THIDS = thread.new("scripts/thread/thread_plugins.lua")

if files.exists("ux0:/app/ONEUPDATE") then
	game.delete("ONEUPDATE") -- Exists delete update app
end

--Creamos nuestra carpeta principal de Trabajo
files.mkdir("ux0:data/AUTOPLUGIN2/")
__PATH_INI    = "ux0:data/AUTOPLUGIN2/config.ini"

--Sprites para Botones
buttonskey = image.load("imgs/buttons.png",20,20)
buttonskey2 = image.load("imgs/buttons2.png",20,20)
buttonskey3 = image.load("imgs/buttons3.png",35,25)
dotg = image.load("imgs/dot_green.png")
doty = image.load("imgs/dot_yellow.png")

__LANG = ini.read(__PATH_INI,"LANGUAGE","lang","")
if __LANG == "" then __LANG = os.language() end
dofile("scripts/language.lua")

if snd then
	sound.loop(snd)
	snd:play(1)
end

dofile("addons/stars.lua")
dofile("scripts/commons.lua")
dofile("scripts/scroll.lua")

-- Loading font
files.mkdir("ux0:data/AUTOPLUGIN2/font/")
fnt,type_fnt = nil, __FONT_TYPE_PGF
__FONT = ini.read(__PATH_INI,"FONT","font","")

if __FONT != "" then
	if __FONT == "font.pvf" then
		font.setdefault(__FONT_TYPE_PVF)
		type_fnt = __FONT_TYPE_PVF
	else
		fnt = font.load("ux0:data/AUTOPLUGIN2/font/"..__FONT)
		if fnt then
			font.setdefault(fnt)
			type_fnt = font.type(fnt)
		end
	end
else
	if __LANG == "POLISH" then
		font.setdefault(__FONT_TYPE_PVF)
		type_fnt = __FONT_TYPE_PVF
	end
end

if __LANG == "CHINESE_T" or __LANG == "CHINESE_S" or __LANG == "TURKISH" then
	if not files.exists("ux0:data/AUTOPLUGIN2/font/font.pgf") then
		if back then back:blit(0,0) end
			message_wait(LANGUAGE["CHINESE_FONT_DOWNLOAD"])
		os.delay(500)
		__file = "font.pgf"
			http.download(string.format("https://gh-proxy.com/https://raw.githubusercontent.com/%s/%s/master/font/font.pgf", APP_REPO, APP_PROJECT), "ux0:data/AUTOPLUGIN2/font/font.pgf")
		__file = ""
	end
	if not fnt then
		fnt, __FONT = font.load("ux0:data/AUTOPLUGIN2/font/font.pgf"), "font.pgf"
		if fnt then
			font.setdefault(fnt)
			type_fnt = font.type(fnt)
		end
	end
end

if os.access() == 0 then
	if back then back:blit(0,0) end
	screen.flip()
	os.message(LANGUAGE["STRING_UNSAFE_MODE"])
	os.exit()
end

__AUTO = tonumber(ini.read(__PATH_INI,"TAI","auto","1"))
if __AUTO == 1 then _autotai = LANGUAGE["YES"] else _autotai = LANGUAGE["NO"] end

__UPDATE = tonumber(ini.read(__PATH_INI,"UPDATE","update","1"))
_update = LANGUAGE["NO"]
if __UPDATE == 1 then
	_update = LANGUAGE["YES"]
	dofile("git/updater.lua")
end
write_config()

dofile("scripts/tai.lua")
tai.load()

if tai.find("KERNEL", "sharpscale.skprx") and not tai.check("!AKRK00005") then
	tai.putBeforeSection("ALL","*!AKRK00005","")
	tai.sync()
	change = true
	if back then back:blit(0,0) end
	screen.flip()
	os.message(LANGUAGE["REPAIR_CONFIG_SHARPSCALE"])
end

-- Repair henkaku: tai,sync() with safeguards
if not tai.hasHenkakuVariant() then
    tai.sync()  -- <-- ahora es la versión con safeguards
    if back then back:blit(0,0) end
    screen.flip()
    os.message(LANGUAGE["REPAIR_CONFIG_TXT"])
end

 dofile("scripts/psvita/menu_psvita.lua")
dofile("scripts/psp/menu_psp.lua")
dofile("scripts/extras/menu_extras.lua")
dofile("scripts/settings/menu_settings.lua")
dofile("scripts/extras/downloads.lua")

--Main Cycle
dofile("menu.lua")
